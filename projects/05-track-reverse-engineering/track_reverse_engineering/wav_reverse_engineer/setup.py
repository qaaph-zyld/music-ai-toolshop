from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wav-reverse-engineer",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A powerful tool for analyzing and reverse engineering WAV audio files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/qaaph-zyld/track_reverse_engineering",
    packages=["wav_reverse_engineer"] + [p for p in find_packages() if p != "wav_reverse_engineer"],
    package_dir={"wav_reverse_engineer": "."},
    package_data={
        'audio_analyzer': ['*.py'],
    },
    install_requires=[
        'librosa>=0.10.0',
        'numpy>=1.20.0',
        'matplotlib>=3.5.0',
        'scipy>=1.7.0',
        'pydub>=0.25.1',
        'pretty_midi>=0.2.10',
        'scikit-learn>=1.0.0',
        'soundfile>=0.10.3',
        'python-rtmidi>=1.4.9',
        'streamlit>=1.35.0',
        'pyloudnorm>=0.1.0',
        'yt-dlp>=2024.1.0',
    ],
    extras_require={
        'pitch': ['torch>=1.12.0', 'torchcrepe>=0.0.22'],
        # Spleeter has limited Python support; skip on Python >=3.12
        'separation': [
            'spleeter>=2.1.0; python_version < "3.12"',
            'demucs>=4.0.0',
            'torch>=1.12.0'
        ],
        # Essentia wheels are not available on Windows via pip; skip on Windows
        'essentia': ['essentia; platform_system != "Windows"'],
        'rhythm': ['madmom>=0.16.1; python_version < "3.12"'],
        'panns': ['panns-inference>=0.1.0', 'torch>=1.12.0'],
        'transcription': ['basic-pitch; platform_system != "Windows"'],
        'api': ['fastapi>=0.109.0', 'uvicorn[standard]>=0.22.0'],
        'evaluation': ['mir_eval>=0.7'],
        'youtube': ['yt-dlp>=2024.1.0'],
        'full': [
            'torch>=1.12.0', 'torchcrepe>=0.0.22',
            'spleeter>=2.1.0; python_version < "3.12"',
            'demucs>=4.0.0', 'panns-inference>=0.1.0',
            'essentia; platform_system != "Windows"', 'madmom>=0.16.1; python_version < "3.12"',
            'basic-pitch; platform_system != "Windows"',
            'fastapi>=0.109.0', 'uvicorn[standard]>=0.22.0', 'mir_eval>=0.7',
            'yt-dlp>=2024.1.0'
        ]
    },
    entry_points={
        'console_scripts': [
            'wav-reverse-engineer=wav_reverse_engineer.cli:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
    ],
    python_requires='>=3.7',
)
