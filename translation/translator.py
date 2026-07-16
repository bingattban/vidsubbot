"""
Translation engine using Argos Translate and other offline engines.
"""
import asyncio
from typing import List, Optional
import argostranslate.package
import argostranslate.translate

from utils.logging import setup_logging

logger = setup_logging(__name__)


class TranslationEngine:
    """Offline translation using Argos Translate."""
    
    def __init__(self) -> None:
        """Initialize translation engine."""
        self._installed_languages = set()
        self._initialize_translator()
    
    def _initialize_translator(self) -> None:
        """Initialize Argos Translate and install required packages."""
        try:
            # Update package index
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # Install Arabic translation packages
            for package in available_packages:
                if package.to_code == 'ar' or package.from_code == 'ar':
                    if package not in argostranslate.package.get_installed_packages():
                        argostranslate.package.install_from_path(package.download())
                        logger.info(f"Installed translation package: {package.from_code} -> {package.to_code}")
            
            # Get installed languages
            self._installed_languages = set()
            for lang in argostranslate.translate.get_installed_languages():
                self._installed_languages.add(lang.code)
            
            logger.info(f"Translation engine initialized with languages: {self._installed_languages}")
            
        except Exception as e:
            logger.error(f"Failed to initialize translation engine: {e}")
            raise
    
    async def translate_text(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ar"
    ) -> str:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        try:
            # Get language objects
            from_lang = None
            to_lang = None
            
            for lang in argostranslate.translate.get_installed_languages():
                if lang.code == source_lang:
                    from_lang = lang
                if lang.code == target_lang:
                    to_lang = lang
            
            if not from_lang or not to_lang:
                # Fallback: try to use any available language as intermediate
                logger.warning(f"Direct translation not available: {source_lang} -> {target_lang}")
                return await self._translate_with_intermediate(text, target_lang)
            
            # Perform translation
            translation = await asyncio.to_thread(
                from_lang.get_translation(to_lang).translate,
                text
            )
            
            return translation
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text
    
    async def _translate_with_intermediate(
        self,
        text: str,
        target_lang: str
    ) -> str:
        """
        Translate using English as intermediate if direct translation not available.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        try:
            # First translate to English if needed
            from_lang = None
            en_lang = None
            ar_lang = None
            
            for lang in argostranslate.translate.get_installed_languages():
                if lang.code == 'en':
                    en_lang = lang
                if lang.code == target_lang:
                    ar_lang = lang
            
            if not en_lang or not ar_lang:
                return text
            
            # Auto-detect source language
            detected_lang = self._detect_language(text)
            
            for lang in argostranslate.translate.get_installed_languages():
                if lang.code == detected_lang:
                    from_lang = lang
                    break
            
            if from_lang and from_lang != en_lang:
                # Translate to English first
                to_en = from_lang.get_translation(en_lang)
                if to_en:
                    text = await asyncio.to_thread(to_en.translate, text)
            
            # Translate English to Arabic
            to_ar = en_lang.get_translation(ar_lang)
            if to_ar:
                text = await asyncio.to_thread(to_ar.translate, text)
            
            return text
            
        except Exception as e:
            logger.error(f"Intermediate translation failed: {e}")
            return text
    
    def _detect_language(self, text: str) -> str:
        """
        Simple language detection based on character sets.
        
        Args:
            text: Text to detect language for
            
        Returns:
            Detected language code
        """
        # Simple heuristic: check for Arabic characters
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
        if arabic_chars > len(text) * 0.5:
            return 'ar'
        
        # Default to English
        return 'en'
    
    async def translate_segments(
        self,
        segments: List[dict],
        target_lang: str = "ar"
    ) -> List[dict]:
        """
        Translate subtitle segments.
        
        Args:
            segments: List of segments with text to translate
            target_lang: Target language code
            
        Returns:
            List of translated segments preserving timing
        """
        try:
            translated_segments = []
            
            for segment in segments:
                translated_text = await self.translate_text(
                    segment['text'],
                    target_lang=target_lang
                )
                
                translated_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': translated_text,
                })
            
            logger.info(f"Translated {len(segments)} segments")
            return translated_segments
            
        except Exception as e:
            logger.error(f"Segment translation failed: {e}")
            raise