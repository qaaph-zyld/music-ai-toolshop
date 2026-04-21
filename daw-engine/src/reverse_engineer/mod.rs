//! Production Reverse Engineering Module
//!
//! Provides spectral analysis, delta comparison, and fingerprinting
//! to reverse-engineer mix/mastering processing chains from audio variants.

pub mod spectral;
pub mod delta;
pub mod fingerprint;

pub use spectral::{SpectralAnalyzer, SpectralFeatures};
pub use delta::{DeltaAnalyzer, DeltaFeatures, ProcessingDetection};
pub use fingerprint::{Fingerprint, FingerprintDatabase};
