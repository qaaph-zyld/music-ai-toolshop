"""
Production Chain Classifier

Machine learning classifier for identifying mix/mastering processing chains
from audio fingerprints. Uses scikit-learn for clustering and classification.
"""

from __future__ import annotations
import json
import pickle
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
from pathlib import Path

# Optional ML dependencies - gracefully degrade if not available
try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. ML features disabled.")


@dataclass
class ProcessingChain:
    """Identified processing chain configuration."""
    chain_id: str
    name: str
    description: str
    eq_profile: str  # e.g., "bright", "warm", "scooped"
    compression_style: str  # e.g., "transparent", "aggressive", "glue"
    spatial_processing: str  # e.g., "wide", "narrow", "mono-compatible"
    loudness_target: str  # e.g., "-14 LUFS", "-9 LUFS", "-6 LUFS"
    confidence: float
    example_tracks: List[str]


@dataclass
class FeatureVector:
    """Normalized feature vector for ML."""
    centroid_norm: float
    rolloff_norm: float
    flatness: float
    crest_factor_norm: float
    rms_db_norm: float
    lufs_db_norm: float
    zcr: float
    bandwidth_norm: float
    
    def to_array(self) -> np.ndarray:
        return np.array([
            self.centroid_norm,
            self.rolloff_norm,
            self.flatness,
            self.crest_factor_norm,
            self.rms_db_norm,
            self.lufs_db_norm,
            self.zcr,
            self.bandwidth_norm,
        ])


class ChainClassifier:
    """Classify audio by processing chain using ML."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.scaler: Optional[StandardScaler] = None
        self.clusterer: Optional[KMeans] = None
        self.classifier: Optional[RandomForestClassifier] = None
        self.is_trained = False
        
        if not SKLEARN_AVAILABLE:
            print("Warning: scikit-learn not available. Using rule-based fallback.")
    
    def _normalize_features(self, features: Dict[str, float]) -> FeatureVector:
        """Normalize raw features to comparable ranges."""
        return FeatureVector(
            centroid_norm=features.get('centroid', 0) / 10000.0,
            rolloff_norm=features.get('rolloff', 0) / 20000.0,
            flatness=features.get('flatness', 0),
            crest_factor_norm=features.get('crest_factor', 0) / 20.0,
            rms_db_norm=(features.get('rms_db', -60) + 60) / 60.0,
            lufs_db_norm=(features.get('lufs_estimate', -60) + 60) / 60.0,
            zcr=features.get('zcr', 0),
            bandwidth_norm=features.get('bandwidth', 0) / 5000.0,
        )
    
    def train(self, fingerprints: List[Dict[str, Any]], chain_labels: List[str]):
        """Train classifier on labeled fingerprint data."""
        if not SKLEARN_AVAILABLE:
            print("Error: Cannot train without scikit-learn")
            return False
        
        # Extract feature vectors
        X = []
        for fp in fingerprints:
            vec = self._normalize_features(fp)
            X.append(vec.to_array())
        
        X = np.array(X)
        y = np.array(chain_labels)
        
        # Normalize features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train classifier
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.classifier.fit(X_scaled, y)
        
        self.is_trained = True
        print(f"Trained classifier on {len(fingerprints)} samples")
        return True
    
    def classify(self, features: Dict[str, float]) -> Optional[ProcessingChain]:
        """Classify a single fingerprint."""
        if not SKLEARN_AVAILABLE or not self.is_trained:
            return self._rule_based_classify(features)
        
        # Normalize and classify
        vec = self._normalize_features(features)
        X = vec.to_array().reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        prediction = self.classifier.predict(X_scaled)[0]
        probabilities = self.classifier.predict_proba(X_scaled)[0]
        confidence = float(np.max(probabilities))
        
        return self._create_chain_result(prediction, confidence)
    
    def _rule_based_classify(self, features: Dict[str, float]) -> ProcessingChain:
        """Fallback rule-based classification when ML not available."""
        centroid = features.get('centroid', 0)
        crest_factor = features.get('crest_factor', 0)
        lufs = features.get('lufs_estimate', -60)
        flatness = features.get('flatness', 0.5)
        
        # Determine EQ profile
        if centroid > 4000:
            eq_profile = "bright"
        elif centroid < 1500:
            eq_profile = "warm"
        else:
            eq_profile = "balanced"
        
        # Determine compression
        if crest_factor < 8:
            compression_style = "heavy"
        elif crest_factor < 12:
            compression_style = "moderate"
        else:
            compression_style = "light"
        
        # Determine spatial characteristics
        if flatness > 0.6:
            spatial_processing = "wide"
        elif flatness < 0.3:
            spatial_processing = "focused"
        else:
            spatial_processing = "neutral"
        
        # Determine loudness target
        if lufs > -10:
            loudness_target = "-9 LUFS (streaming loud)"
        elif lufs > -16:
            loudness_target = "-14 LUFS (standard)"
        else:
            loudness_target = "-23 LUFS (broadcast)"
        
        # Build description
        description = f"{eq_profile.title()} EQ with {compression_style} compression, {spatial_processing} spatial image"
        
        # Determine chain type
        if compression_style == "heavy" and lufs > -12:
            chain_id = "master_aggressive"
            name = "Aggressive Master"
        elif eq_profile == "bright" and compression_style == "light":
            chain_id = "mix_pop"
            name = "Pop Mix"
        elif eq_profile == "warm" and compression_style == "moderate":
            chain_id = "mix_acoustic"
            name = "Acoustic Mix"
        else:
            chain_id = "general"
            name = "General Production"
        
        return ProcessingChain(
            chain_id=chain_id,
            name=name,
            description=description,
            eq_profile=eq_profile,
            compression_style=compression_style,
            spatial_processing=spatial_processing,
            loudness_target=loudness_target,
            confidence=0.6,  # Rule-based has lower confidence
            example_tracks=[],
        )
    
    def _create_chain_result(self, prediction: str, confidence: float) -> ProcessingChain:
        """Create chain result from prediction."""
        chain_templates = {
            "master_aggressive": {
                "name": "Aggressive Master",
                "description": "Heavy limiting with bright EQ for competitive loudness",
                "eq_profile": "bright",
                "compression_style": "aggressive",
                "spatial_processing": "wide",
                "loudness_target": "-9 LUFS",
            },
            "master_conservative": {
                "name": "Conservative Master",
                "description": "Transparent processing preserving dynamics",
                "eq_profile": "balanced",
                "compression_style": "transparent",
                "spatial_processing": "mono-compatible",
                "loudness_target": "-14 LUFS",
            },
            "mix_pop": {
                "name": "Pop Mix Template",
                "description": "Bright, punchy mix with scooped mids",
                "eq_profile": "scooped",
                "compression_style": "glue",
                "spatial_processing": "wide",
                "loudness_target": "-18 LUFS (mix)",
            },
            "mix_acoustic": {
                "name": "Acoustic Mix Template",
                "description": "Warm, natural mix with preserved dynamics",
                "eq_profile": "warm",
                "compression_style": "transparent",
                "spatial_processing": "natural",
                "loudness_target": "-20 LUFS (mix)",
            },
            "edm_drop": {
                "name": "EDM Drop Chain",
                "description": "Maximized for club play with heavy sidechain",
                "eq_profile": "bass-heavy",
                "compression_style": "pumping",
                "spatial_processing": "ultra-wide",
                "loudness_target": "-6 LUFS",
            },
        }
        
        template = chain_templates.get(prediction, {
            "name": f"Chain: {prediction}",
            "description": "Custom processing chain",
            "eq_profile": "unknown",
            "compression_style": "unknown",
            "spatial_processing": "unknown",
            "loudness_target": "unknown",
        })
        
        return ProcessingChain(
            chain_id=prediction,
            name=template["name"],
            description=template["description"],
            eq_profile=template["eq_profile"],
            compression_style=template["compression_style"],
            spatial_processing=template["spatial_processing"],
            loudness_target=template["loudness_target"],
            confidence=confidence,
            example_tracks=[],
        )
    
    def cluster_fingerprints(
        self, 
        fingerprints: List[Dict[str, Any]], 
        n_clusters: int = 5
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Cluster fingerprints by similarity using K-means."""
        if not SKLEARN_AVAILABLE:
            return self._rule_based_cluster(fingerprints)
        
        # Extract feature vectors
        X = []
        for fp in fingerprints:
            vec = self._normalize_features(fp)
            X.append(vec.to_array())
        
        X = np.array(X)
        
        # Normalize
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Apply PCA for dimensionality reduction
        pca = PCA(n_components=min(4, X.shape[1]))
        X_pca = pca.fit_transform(X_scaled)
        
        # Cluster
        self.clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = self.clusterer.fit_predict(X_pca)
        
        # Group by cluster
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(fingerprints[i])
        
        return clusters
    
    def _rule_based_cluster(
        self, 
        fingerprints: List[Dict[str, Any]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Rule-based clustering when ML not available."""
        clusters: Dict[int, List[Dict[str, Any]]] = {
            0: [],  # Bright/Heavy
            1: [],  # Warm/Light
            2: [],  # Balanced
            3: [],  # Loud/Mastered
        }
        
        for fp in fingerprints:
            centroid = fp.get('centroid', 0)
            crest = fp.get('crest_factor', 0)
            lufs = fp.get('lufs_estimate', -60)
            
            # Simple rule-based assignment
            if lufs > -12:
                clusters[3].append(fp)  # Loud/Mastered
            elif centroid > 3000 and crest < 10:
                clusters[0].append(fp)  # Bright/Heavy
            elif centroid < 2000 and crest > 12:
                clusters[1].append(fp)  # Warm/Light
            else:
                clusters[2].append(fp)  # Balanced
        
        # Remove empty clusters
        return {k: v for k, v in clusters.items() if v}
    
    def save_model(self, path: str):
        """Save trained model to disk."""
        if not SKLEARN_AVAILABLE or not self.is_trained:
            print("Error: No trained model to save")
            return False
        
        model_data = {
            'scaler': self.scaler,
            'classifier': self.classifier,
            'clusterer': self.clusterer,
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {path}")
        return True
    
    def load_model(self, path: str) -> bool:
        """Load trained model from disk."""
        if not SKLEARN_AVAILABLE:
            print("Error: Cannot load model without scikit-learn")
            return False
        
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.scaler = model_data.get('scaler')
            self.classifier = model_data.get('classifier')
            self.clusterer = model_data.get('clusterer')
            self.is_trained = self.classifier is not None
            
            print(f"Model loaded from {path}")
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def suggest_processing_chain(
        self, 
        reference_features: Dict[str, float],
        target_features: Dict[str, float]
    ) -> Dict[str, Any]:
        """Suggest processing chain to match reference."""
        ref_chain = self.classify(reference_features)
        target_chain = self.classify(target_features)
        
        if not ref_chain or not target_chain:
            return {"error": "Classification failed"}
        
        suggestions = {
            "reference_chain": ref_chain,
            "current_chain": target_chain,
            "recommendations": [],
        }
        
        # Compare and suggest
        if ref_chain.eq_profile != target_chain.eq_profile:
            suggestions["recommendations"].append({
                "type": "eq",
                "current": target_chain.eq_profile,
                "target": ref_chain.eq_profile,
                "suggestion": f"Adjust EQ toward {ref_chain.eq_profile} profile",
            })
        
        if ref_chain.compression_style != target_chain.compression_style:
            suggestions["recommendations"].append({
                "type": "compression",
                "current": target_chain.compression_style,
                "target": ref_chain.compression_style,
                "suggestion": f"Adjust compression to {ref_chain.compression_style} style",
            })
        
        if ref_chain.loudness_target != target_chain.loudness_target:
            suggestions["recommendations"].append({
                "type": "limiting",
                "current_lufs": target_chain.loudness_target,
                "target_lufs": ref_chain.loudness_target,
                "suggestion": f"Adjust limiting for {ref_chain.loudness_target} target",
            })
        
        return suggestions


def demo():
    """Demo the classifier with synthetic data."""
    print("Production Chain Classifier Demo")
    print("=" * 50)
    
    classifier = ChainClassifier()
    
    # Create synthetic fingerprints
    test_cases = [
        {
            "name": "Bright Pop Master",
            "centroid": 4500,
            "rolloff": 12000,
            "flatness": 0.3,
            "crest_factor": 8,
            "rms_db": -12,
            "peak_db": -6,
            "lufs_estimate": -10,
            "zcr": 0.08,
            "bandwidth": 3000,
        },
        {
            "name": "Warm Acoustic Mix",
            "centroid": 1200,
            "rolloff": 4000,
            "flatness": 0.6,
            "crest_factor": 15,
            "rms_db": -20,
            "peak_db": -12,
            "lufs_estimate": -22,
            "zcr": 0.05,
            "bandwidth": 1500,
        },
        {
            "name": "EDM Drop",
            "centroid": 3500,
            "rolloff": 18000,
            "flatness": 0.2,
            "crest_factor": 6,
            "rms_db": -8,
            "peak_db": -3,
            "lufs_estimate": -6,
            "zcr": 0.12,
            "bandwidth": 4000,
        },
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}:")
        print("-" * 30)
        
        chain = classifier.classify(test)
        print(f"  Detected Chain: {chain.name}")
        print(f"  Description: {chain.description}")
        print(f"  Confidence: {chain.confidence:.0%}")
        print(f"  EQ: {chain.eq_profile}")
        print(f"  Compression: {chain.compression_style}")
        print(f"  Loudness: {chain.loudness_target}")


if __name__ == "__main__":
    demo()
