#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Processamento de Logos
Redimensiona e otimiza logos automaticamente
"""

import logging
from PIL import Image
import os
from pathlib import Path
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# ConfiguraÃ§Ãµes de logos
LOGO_TYPES = {
    "square": {
        "name": "Quadrada",
        "size": (400, 400),
        "aspect_ratio": "1:1",
        "description": "Para Ã­cones, perfis e redes sociais",
        "max_size_mb": 2,
    },
    "vertical": {
        "name": "Retangular Vertical",
        "size": (300, 600),
        "aspect_ratio": "1:2",
        "description": "Para documentos em formato retrato",
        "max_size_mb": 2,
    },
    "horizontal": {
        "name": "Retangular Horizontal",
        "size": (800, 400),
        "aspect_ratio": "2:1",
        "description": "Para cabeÃ§alhos e assinaturas",
        "max_size_mb": 2,
    },
    "banner": {
        "name": "Banner",
        "size": (1200, 300),
        "aspect_ratio": "4:1",
        "description": "Para topo de documentos e apresentaÃ§Ãµes",
        "max_size_mb": 3,
    },
}

UPLOAD_FOLDER = "uploads/logos"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}


def init_logo_folders():
    """Cria pastas necessÃ¡rias para logos"""
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)


def allowed_file(filename):
    """Verifica se extensÃ£o Ã© permitida"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def resize_and_save_logo(image_file, company_id, logo_type):
    """
    Redimensiona e salva logo no tamanho correto

    Args:
        image_file: Arquivo de imagem do upload
        company_id: ID da empresa
        logo_type: 'square', 'vertical', 'horizontal', 'banner'

    Returns:
        str: Caminho relativo do arquivo salvo ou None se erro
    """

    if logo_type not in LOGO_TYPES:
        raise ValueError(f"Tipo de logo invÃ¡lido: {logo_type}")

    if not allowed_file(image_file.filename):
        raise ValueError("ExtensÃ£o de arquivo nÃ£o permitida")

    # ConfiguraÃ§Ãµes do tipo de logo
    config = LOGO_TYPES[logo_type]
    target_size = config["size"]

    # Criar pasta se nÃ£o existe
    init_logo_folders()

    # Nome do arquivo
    ext = image_file.filename.rsplit(".", 1)[1].lower()
    safe_filename = f"company_{company_id}_{logo_type}.{ext}"
    file_path = Path(UPLOAD_FOLDER) / safe_filename

    try:
        # Abrir imagem
        img = Image.open(image_file)

        # Converter RGBA para RGB se necessÃ¡rio (para JPG)
        if img.mode in ("RGBA", "LA", "P") and ext in ("jpg", "jpeg"):
            # Criar fundo branco
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background

        # Calcular redimensionamento mantendo proporÃ§Ã£o
        img.thumbnail(target_size, Image.Resampling.LANCZOS)

        # Criar imagem final com fundo branco se menor que target
        final_img = Image.new(
            "RGB" if ext in ("jpg", "jpeg") else "RGBA",
            target_size,
            (255, 255, 255, 0) if ext not in ("jpg", "jpeg") else (255, 255, 255),
        )

        # Centralizar a imagem redimensionada
        offset = (
            (target_size[0] - img.size[0]) // 2,
            (target_size[1] - img.size[1]) // 2,
        )
        final_img.paste(img, offset)

        # Salvar com otimizaÃ§Ã£o
        save_kwargs = {"optimize": True, "quality": 90}
        if ext == "png":
            save_kwargs["compress_level"] = 9

        final_img.save(str(file_path), **save_kwargs)

        # Retornar caminho relativo
        return f"{UPLOAD_FOLDER}/{safe_filename}"

    except Exception as e:
        logger.exception("Erro ao processar logo")
        raise


def delete_logo(logo_path):
    """Deleta um logo do sistema de arquivos"""
    if logo_path:
        try:
            file_path = Path(logo_path)
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            logger.exception("Erro ao deletar logo")
    return False


def get_logo_url(logo_path):
    """Converte caminho do logo para URL"""
    if logo_path:
        return f"/{logo_path}"
    return None


def get_logo_config(logo_type):
    """Retorna configuraÃ§Ã£o de um tipo de logo"""
    return LOGO_TYPES.get(logo_type)


def get_all_logo_configs():
    """Retorna todas as configuraÃ§Ãµes de logos"""
    return LOGO_TYPES
