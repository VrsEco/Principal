#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualizador Periódico de Placeholders
Sistema PEVAPP22
Executa automaticamente para manter os dados de exemplo atualizados
"""

import os
import sys
import schedule
import time
from datetime import datetime

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.placeholder_generator import PlaceholderGenerator


class PlaceholderScheduler:
    """
    Agendador para atualização automática de placeholders
    """

    def __init__(self):
        self.generator = PlaceholderGenerator()
        self.log_file = "placeholder_update.log"

    def log(self, message):
        """Registra log com timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        print(log_entry)

        # Salva no arquivo de log
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Erro ao salvar log: {e}")

    def update_placeholders(self):
        """Executa atualização dos placeholders"""
        try:
            self.log("🔄 Iniciando atualização de placeholders...")

            updated = self.generator.update_all_placeholders()

            if updated:
                self.log(f"✅ {len(updated)} placeholders atualizados:")
                for item in updated:
                    self.log(f"   - {item['type']}: {item['records']}")
            else:
                self.log("⚠️ Nenhum placeholder foi atualizado")

        except Exception as e:
            self.log(f"❌ Erro durante atualização: {str(e)}")

    def setup_schedule(self):
        """Configura os agendamentos"""
        # Atualiza a cada 6 horas
        schedule.every(6).hours.do(self.update_placeholders)

        # Atualização diária às 08:00
        schedule.every().day.at("08:00").do(self.update_placeholders)

        # Atualização de segunda-feira às 06:00 (mais completa)
        schedule.every().monday.at("06:00").do(self.update_placeholders)

        self.log("⏰ Agendamentos configurados:")
        self.log("   - A cada 6 horas")
        self.log("   - Diariamente às 08:00")
        self.log("   - Segundas-feiras às 06:00")

    def run_once(self):
        """Executa uma vez (para testes)"""
        self.log("🚀 Executando atualização única...")
        self.update_placeholders()

    def run_scheduler(self):
        """Executa o agendador continuamente"""
        self.setup_schedule()
        self.log("🌟 Agendador de placeholders iniciado")

        # Executa uma atualização inicial
        self.update_placeholders()

        # Loop principal
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
        except KeyboardInterrupt:
            self.log("🔴 Agendador interrompido pelo usuário")
        except Exception as e:
            self.log(f"💥 Erro crítico no agendador: {str(e)}")


def main():
    """Função principal"""
    scheduler = PlaceholderScheduler()

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Executa uma única vez
        scheduler.run_once()
    else:
        # Executa continuamente
        scheduler.run_scheduler()


if __name__ == "__main__":
    main()
