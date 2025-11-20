"""
APP25 - Serviço de Análise de Reputação Online
"""

import requests
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReputationService:
    """
    Serviço para análise de reputação online de empresas
    """

    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.timeout = 30

    def search_company_reputation(
        self, company_name: str, cnpj: str = None
    ) -> Dict[str, Any]:
        """
        Busca informações de reputação da empresa em diferentes fontes

        Args:
            company_name: Nome da empresa
            cnpj: CNPJ da empresa (opcional)

        Returns:
            Dicionário com resultados da análise de reputação
        """
        try:
            results = {
                "company_name": company_name,
                "cnpj": cnpj,
                "analysis_date": datetime.now().isoformat(),
                "sources": {},
                "summary": {},
                "recommendations": [],
            }

            # Buscar em diferentes fontes
            results["sources"]["google_search"] = self._search_google(company_name)
            results["sources"]["news_search"] = self._search_news(company_name)
            results["sources"]["social_media"] = self._search_social_media(company_name)

            if cnpj:
                results["sources"]["cnpj_info"] = self._search_cnpj_info(cnpj)

            # Gerar resumo e recomendações
            results["summary"] = self._generate_summary(results["sources"])
            results["recommendations"] = self._generate_recommendations(
                results["sources"]
            )

            return results

        except Exception as e:
            logger.error(f"Erro na análise de reputação: {e}")
            return {
                "error": str(e),
                "company_name": company_name,
                "analysis_date": datetime.now().isoformat(),
            }

    def _search_google(self, company_name: str) -> Dict[str, Any]:
        """Simula busca no Google (em produção, usaria Google Custom Search API)"""
        try:
            # Simulação de resultados do Google
            return {
                "status": "success",
                "results": [
                    {
                        "title": f"{company_name} - Site Oficial",
                        "url": f'https://www.{company_name.lower().replace(" ", "")}.com.br',
                        "snippet": f"Site oficial da {company_name} com informações sobre produtos e serviços.",
                        "relevance": "high",
                    },
                    {
                        "title": f"{company_name} - LinkedIn",
                        "url": f'https://linkedin.com/company/{company_name.lower().replace(" ", "-")}',
                        "snippet": f"Perfil corporativo da {company_name} no LinkedIn.",
                        "relevance": "medium",
                    },
                ],
                "total_results": 2,
                "search_time": "0.45s",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_news(self, company_name: str) -> Dict[str, Any]:
        """Simula busca de notícias (em produção, usaria News API)"""
        try:
            # Simulação de resultados de notícias
            return {
                "status": "success",
                "articles": [
                    {
                        "title": f"{company_name} anuncia nova estratégia de crescimento",
                        "source": "Portal de Negócios",
                        "date": "2024-01-15",
                        "sentiment": "positive",
                        "url": f'https://portalnegocios.com/{company_name.lower().replace(" ", "-")}-crescimento',
                    },
                    {
                        "title": f"{company_name} recebe prêmio de inovação",
                        "source": "Revista Tecnologia",
                        "date": "2024-01-10",
                        "sentiment": "positive",
                        "url": f'https://revistatech.com/{company_name.lower().replace(" ", "-")}-premio',
                    },
                ],
                "total_articles": 2,
                "sentiment_score": 0.8,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_social_media(self, company_name: str) -> Dict[str, Any]:
        """Simula busca em redes sociais"""
        try:
            return {
                "status": "success",
                "platforms": {
                    "linkedin": {
                        "followers": 1250,
                        "engagement_rate": 0.045,
                        "recent_posts": 3,
                        "sentiment": "positive",
                    },
                    "facebook": {
                        "followers": 890,
                        "engagement_rate": 0.032,
                        "recent_posts": 2,
                        "sentiment": "neutral",
                    },
                    "instagram": {
                        "followers": 2100,
                        "engagement_rate": 0.067,
                        "recent_posts": 5,
                        "sentiment": "positive",
                    },
                },
                "overall_sentiment": "positive",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_cnpj_info(self, cnpj: str) -> Dict[str, Any]:
        """Simula busca de informações do CNPJ"""
        try:
            # Simulação de dados do CNPJ
            return {
                "status": "success",
                "cnpj": cnpj,
                "company_info": {
                    "legal_name": "TechCorp Solutions Ltda",
                    "trade_name": "TechCorp Solutions",
                    "status": "Ativa",
                    "opening_date": "2016-03-15",
                    "legal_nature": "Sociedade Empresária Limitada",
                    "main_activity": "Desenvolvimento de software",
                    "address": "São Paulo, SP",
                },
                "financial_info": {
                    "capital_social": "R$ 100.000,00",
                    "revenue_range": "R$ 2.000.001 a R$ 5.000.000",
                    "employees_range": "21 a 50 funcionários",
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_summary(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo da análise de reputação"""
        try:
            summary = {
                "overall_score": 0,
                "positive_indicators": [],
                "negative_indicators": [],
                "neutral_indicators": [],
                "key_findings": [],
            }

            # Analisar resultados do Google
            if sources.get("google_search", {}).get("status") == "success":
                summary["positive_indicators"].append("Presença online estabelecida")
                summary["key_findings"].append("Site oficial encontrado")
                summary["overall_score"] += 20

            # Analisar notícias
            if sources.get("news_search", {}).get("status") == "success":
                articles = sources["news_search"].get("articles", [])
                positive_news = len(
                    [a for a in articles if a.get("sentiment") == "positive"]
                )
                if positive_news > 0:
                    summary["positive_indicators"].append(
                        f"{positive_news} notícias positivas recentes"
                    )
                    summary["overall_score"] += 15

            # Analisar redes sociais
            if sources.get("social_media", {}).get("status") == "success":
                platforms = sources["social_media"].get("platforms", {})
                total_followers = sum(p.get("followers", 0) for p in platforms.values())
                if total_followers > 1000:
                    summary["positive_indicators"].append(
                        f"Presença forte em redes sociais ({total_followers} seguidores)"
                    )
                    summary["overall_score"] += 25

            # Analisar CNPJ
            if sources.get("cnpj_info", {}).get("status") == "success":
                summary["positive_indicators"].append("CNPJ ativo e regular")
                summary["key_findings"].append("Empresa estabelecida há mais de 5 anos")
                summary["overall_score"] += 20

            # Normalizar score (0-100)
            summary["overall_score"] = min(summary["overall_score"], 100)

            return summary

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self, sources: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []

        try:
            # Recomendações baseadas na análise
            if sources.get("google_search", {}).get("status") == "success":
                results = sources["google_search"].get("results", [])
                if len(results) < 5:
                    recommendations.append(
                        "Considere investir em SEO para melhorar a visibilidade online"
                    )

            if sources.get("social_media", {}).get("status") == "success":
                platforms = sources["social_media"].get("platforms", {})
                if len(platforms) < 3:
                    recommendations.append(
                        "Expanda a presença em diferentes redes sociais"
                    )

            if sources.get("news_search", {}).get("status") == "success":
                articles = sources["news_search"].get("articles", [])
                if len(articles) < 3:
                    recommendations.append(
                        "Invista em estratégias de comunicação e relacionamento com a mídia"
                    )

            # Recomendações gerais
            recommendations.extend(
                [
                    "Monitore regularmente menções à empresa online",
                    "Implemente estratégias de marketing digital",
                    "Mantenha informações atualizadas em todos os canais",
                ]
            )

            return recommendations

        except Exception as e:
            logger.error(f"Erro ao gerar recomendações: {e}")
            return ["Erro ao gerar recomendações específicas"]

    def format_analysis_for_ai(self, analysis_data: Dict[str, Any]) -> str:
        """
        Formata os dados da análise para uso em prompts de IA

        Args:
            analysis_data: Dados da análise de reputação

        Returns:
            String formatada para prompt de IA
        """
        try:
            formatted = f"""
# ANÁLISE DE REPUTAÇÃO ONLINE - {analysis_data.get('company_name', 'N/A')}

## RESUMO EXECUTIVO
- **Score Geral**: {analysis_data.get('summary', {}).get('overall_score', 0)}/100
- **Data da Análise**: {analysis_data.get('analysis_date', 'N/A')}

## INDICADORES POSITIVOS
{chr(10).join(f"- {indicator}" for indicator in analysis_data.get('summary', {}).get('positive_indicators', []))}

## INDICADORES NEGATIVOS
{chr(10).join(f"- {indicator}" for indicator in analysis_data.get('summary', {}).get('negative_indicators', []))}

## PRINCIPAIS ACHADOS
{chr(10).join(f"- {finding}" for finding in analysis_data.get('summary', {}).get('key_findings', []))}

## FONTES ANALISADAS
"""

            # Adicionar detalhes das fontes
            sources = analysis_data.get("sources", {})
            for source_name, source_data in sources.items():
                if source_data.get("status") == "success":
                    formatted += f"\n### {source_name.upper().replace('_', ' ')}\n"
                    if source_name == "google_search":
                        results = source_data.get("results", [])
                        for result in results[:3]:  # Limitar a 3 resultados
                            formatted += f"- {result.get('title', 'N/A')}\n"
                    elif source_name == "news_search":
                        articles = source_data.get("articles", [])
                        for article in articles[:3]:  # Limitar a 3 artigos
                            formatted += f"- {article.get('title', 'N/A')} ({article.get('sentiment', 'N/A')})\n"
                    elif source_name == "social_media":
                        platforms = source_data.get("platforms", {})
                        for platform, data in platforms.items():
                            formatted += f"- {platform.title()}: {data.get('followers', 0)} seguidores\n"

            formatted += f"""
## RECOMENDAÇÕES
{chr(10).join(f"- {rec}" for rec in analysis_data.get('recommendations', []))}

---
*Análise gerada automaticamente pelo sistema APP25*
"""

            return formatted

        except Exception as e:
            logger.error(f"Erro ao formatar análise: {e}")
            return f"Erro ao formatar análise: {str(e)}"
