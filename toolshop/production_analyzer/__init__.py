"""
Production Analyzer Module

Analyzes audio variants to reverse-engineer mix/mastering processing chains.

Usage:
    from ai_modules.production_analyzer import BatchAnalyzer, ChainClassifier
    
    # Batch analyze directory
    analyzer = BatchAnalyzer()
    fingerprints = analyzer.analyze_directory("/path/to/audio/files")
    
    # Classify processing chain
    classifier = ChainClassifier()
    chain = classifier.classify(fingerprint_features)
"""

from .batch_analyzer import BatchAnalyzer, AudioFingerprint, ProcessingRecipe
from .classifier import ChainClassifier, ProcessingChain

__all__ = [
    'BatchAnalyzer',
    'AudioFingerprint',
    'ProcessingRecipe',
    'ChainClassifier',
    'ProcessingChain',
]

__version__ = "0.1.0"
