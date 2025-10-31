"""
Cálculo de métricas financeiras corretas para ModeFin
Implementa TIR, VPL, ROI e Pay-back usando fluxo de caixa real do investidor
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal


def calculate_financial_metrics(
    financeiro: Dict[str, Any],
    products_totals: Dict[str, Any],
    resumo_investimentos: List[Dict[str, Any]],
    profit_distribution: List[Dict[str, Any]],
    result_rules: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calcula métricas financeiras corretas (Pay-back, ROI, TIR, VPL)
    usando o fluxo de caixa real do investidor
    """
    
    # Extrair fluxos de caixa do investidor
    fluxo_investidor = financeiro.get('fluxo_investidor', {})
    periodos = fluxo_investidor.get('periodos', [])
    
    if not periodos:
        return _get_empty_metrics()
    
    # Extrair fluxos de caixa (aportes e distribuições)
    fluxos = []
    for periodo in periodos:
        # Aporte (negativo = saída)
        aporte_str = periodo.get('aporte', 'R$ 0,00').replace('R$ ', '').replace('.', '').replace(',', '.')
        try:
            aporte = float(aporte_str)
        except (ValueError, AttributeError):
            aporte = 0.0
        
        # Distribuição (positivo = entrada)
        distribuicao_str = periodo.get('distribuicao', 'R$ 0,00').replace('R$ ', '').replace('.', '').replace(',', '.')
        try:
            distribuicao = float(distribuicao_str)
        except (ValueError, AttributeError):
            distribuicao = 0.0
        
        # Fluxo líquido do investidor (distribuição - aporte)
        fluxo = distribuicao - aporte
        fluxos.append({
            'periodo': periodo.get('periodo', ''),
            'aporte': aporte,
            'distribuicao': distribuicao,
            'fluxo': fluxo
        })
    
    # Calcular totais
    total_aportes = sum(f['aporte'] for f in fluxos)
    total_distribuicoes = sum(f['distribuicao'] for f in fluxos)
    
    # Calcular Pay-back
    payback_meses, payback_inicio, payback_fim = _calculate_payback(fluxos)
    
    # Calcular ROI
    roi_percent = _calculate_roi(total_aportes, total_distribuicoes)
    
    # Obter parâmetros
    periodo_meses = len(fluxos)
    custo_oportunidade_percent = 12.0  # Default 12% a.a.
    
    # Tentar pegar do financeiro se existir
    metrics_data = financeiro.get('fluxo_investidor', {}).get('analises', {})
    if metrics_data:
        try:
            custo_str = str(metrics_data.get('opportunity_cost', '12%')).replace('%', '').strip()
            custo_oportunidade_percent = float(custo_str)
        except (ValueError, TypeError):
            pass
    
    # Calcular VPL
    vpl = _calculate_vpl([f['fluxo'] for f in fluxos], custo_oportunidade_percent)
    
    # Calcular TIR
    tir_percent = _calculate_tir([f['fluxo'] for f in fluxos])
    
    # Calcular investimento total e resultado operacional
    total_investimentos = 0.0
    for item in resumo_investimentos:
        if item.get('is_total'):
            investimentos_str = str(item.get('investimentos', '0')).replace('R$ ', '').replace('.', '').replace(',', '.')
            try:
                total_investimentos = float(investimentos_str)
            except (ValueError, TypeError):
                pass
            break
    
    resultado_operacional = 0.0
    margem = products_totals.get('margem_contribuicao', {})
    if isinstance(margem, dict):
        resultado_operacional = float(margem.get('valor', 0))
    
    return {
        'payback_meses': payback_meses,
        'payback_inicio': payback_inicio,
        'payback_fim': payback_fim,
        'roi_percent': roi_percent,
        'tir_percent': tir_percent,
        'vpl': vpl,
        'total_investimentos': total_investimentos,
        'resultado_operacional': resultado_operacional,
        'periodo_meses': periodo_meses,
        'custo_oportunidade_percent': custo_oportunidade_percent,
    }


def _get_empty_metrics() -> Dict[str, Any]:
    """Retorna métricas vazias"""
    return {
        'payback_meses': None,
        'payback_inicio': None,
        'payback_fim': None,
        'roi_percent': None,
        'tir_percent': None,
        'vpl': None,
        'total_investimentos': 0.0,
        'resultado_operacional': 0.0,
        'periodo_meses': 0,
        'custo_oportunidade_percent': 12.0,
    }


def _calculate_payback(fluxos: List[Dict[str, Any]]) -> tuple:
    """
    Calcula o Pay-back (tempo até recuperar o investimento)
    Retorna: (meses, periodo_inicio, periodo_fim)
    """
    if not fluxos:
        return None, None, None
    
    # Encontrar primeiro mês com aporte
    inicio_idx = None
    inicio_periodo = None
    for idx, f in enumerate(fluxos):
        if f['aporte'] > 0:
            inicio_idx = idx
            inicio_periodo = f['periodo']
            break
    
    if inicio_idx is None:
        return None, None, None
    
    # Calcular saldo acumulado e encontrar quando fica >= 0
    saldo_acumulado = 0.0
    for idx in range(inicio_idx, len(fluxos)):
        saldo_acumulado += fluxos[idx]['fluxo']
        if saldo_acumulado >= 0:
            meses = (idx - inicio_idx) + 1
            fim_periodo = fluxos[idx]['periodo']
            return meses, inicio_periodo, fim_periodo
    
    # Não recuperou ainda
    meses = len(fluxos) - inicio_idx
    return meses, inicio_periodo, None


def _calculate_roi(total_aportes: float, total_distribuicoes: float) -> Optional[float]:
    """
    Calcula o ROI (Retorno sobre Investimento)
    ROI = (Distribuições / Aportes) * 100
    """
    if total_aportes <= 0:
        return None
    
    roi = (total_distribuicoes / total_aportes) * 100
    return roi


def _calculate_vpl(fluxos: List[float], taxa_anual: float) -> float:
    """
    Calcula o VPL (Valor Presente Líquido)
    VPL = Soma dos fluxos descontados pela taxa de desconto
    """
    if not fluxos:
        return 0.0
    
    # Converter taxa anual para mensal
    taxa_mensal = (1 + (taxa_anual / 100.0)) ** (1.0 / 12.0) - 1
    
    vpl = 0.0
    for periodo, fluxo in enumerate(fluxos, start=1):
        valor_presente = fluxo / ((1 + taxa_mensal) ** periodo)
        vpl += valor_presente
    
    return vpl


def _calculate_tir(fluxos: List[float]) -> Optional[float]:
    """
    Calcula a TIR (Taxa Interna de Retorno)
    TIR = Taxa que faz VPL = 0
    Usa método de Newton-Raphson
    """
    if not fluxos:
        return None
    
    # Verificar se há aportes e distribuições
    tem_negativo = any(f < 0 for f in fluxos)
    tem_positivo = any(f > 0 for f in fluxos)
    
    if not (tem_negativo and tem_positivo):
        return None
    
    # Newton-Raphson
    taxa = 0.10  # Chute inicial: 10% ao mês
    max_iteracoes = 100
    precisao = 0.0001
    
    for _ in range(max_iteracoes):
        vpl = 0.0
        derivada = 0.0
        
        for periodo, fluxo in enumerate(fluxos, start=1):
            vpl += fluxo / ((1 + taxa) ** periodo)
            derivada -= (periodo * fluxo) / ((1 + taxa) ** (periodo + 1))
        
        # Se VPL está próximo de zero, encontramos a TIR
        if abs(vpl) < precisao:
            break
        
        # Evitar divisão por zero
        if abs(derivada) < 0.000001:
            break
        
        # Newton-Raphson: x_novo = x_velho - f(x) / f'(x)
        taxa = taxa - vpl / derivada
        
        # Limitar taxa entre -50% e 200% ao mês
        if taxa < -0.5:
            taxa = -0.5
        if taxa > 2.0:
            taxa = 2.0
    
    # Converter para taxa anual equivalente
    tir_anual = ((1 + taxa) ** 12 - 1) * 100
    
    return tir_anual

