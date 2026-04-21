//! Engine Performance Benchmarks
//!
//! Run with: cargo bench
//! Results saved to: target/criterion/

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use daw_engine::{Mixer, SineWave, SamplePlayer, Sample, TransportClock, MidiEngine, MidiNote};

/// Benchmark mixer with varying track counts
fn bench_mixer_process(c: &mut Criterion) {
    let mut group = c.benchmark_group("mixer");
    
    for track_count in [1, 2, 4, 8, 16, 32, 64].iter() {
        group.bench_with_input(
            BenchmarkId::new("process", track_count),
            track_count,
            |b, &track_count| {
                let mut mixer = Mixer::new(2);
                
                // Add sine wave sources
                for i in 0..track_count {
                    let freq = 440.0 + (i as f32 * 10.0);
                    let sine = SineWave::new(freq, 0.1);
                    mixer.add_source(Box::new(sine));
                }
                
                let mut output = vec![0.0f32; 128 * 2]; // 128 frames, stereo
                
                b.iter(|| {
                    mixer.process(black_box(&mut output));
                });
            },
        );
    }
    
    group.finish();
}

/// Benchmark sample player at different buffer sizes
fn bench_sample_player(c: &mut Criterion) {
    let mut group = c.benchmark_group("sample_player");
    
    // Create a 10-second stereo sample at 48kHz
    let sample_data = vec![0.5f32; 48000 * 10 * 2]; // 10 seconds, stereo
    let sample = Sample::from_raw(sample_data, 2, 48000);
    
    for buffer_size in [64, 128, 256, 512, 1024].iter() {
        group.bench_with_input(
            BenchmarkId::new("process_stereo_48k", buffer_size),
            buffer_size,
            |b, &buffer_size| {
                let mut player = SamplePlayer::new(sample.clone(), 2);
                player.play();
                let mut output = vec![0.0f32; buffer_size * 2]; // stereo
                
                b.iter(|| {
                    player.process(black_box(&mut output));
                });
            },
        );
    }
    
    group.finish();
}

/// Benchmark transport clock advancement
fn bench_transport_clock(c: &mut Criterion) {
    let mut group = c.benchmark_group("transport_clock");
    
    for sample_count in [64, 128, 256, 512, 1024, 4096].iter() {
        group.bench_with_input(
            BenchmarkId::new("advance_and_beats", sample_count),
            sample_count,
            |b, &sample_count| {
                let mut clock = TransportClock::new(48000);
                clock.set_tempo(120.0);
                
                b.iter(|| {
                    clock.advance(black_box(sample_count as u64));
                    black_box(clock.beats());
                });
            },
        );
    }
    
    group.finish();
}

/// Benchmark MIDI engine with varying note counts
fn bench_midi_engine(c: &mut Criterion) {
    let mut group = c.benchmark_group("midi_engine");
    
    for note_count in [10, 50, 100, 500, 1000].iter() {
        group.bench_with_input(
            BenchmarkId::new("process_notes", note_count),
            note_count,
            |b, &note_count| {
                let mut engine = MidiEngine::new(16);
                
                // Add notes distributed across channels
                for i in 0..note_count {
                    let channel = i % 16;
                    let note = MidiNote::new(
                        60 + (i % 12) as u8,
                        100,
                        i as f32 * 0.25,
                        0.5,
                    );
                    engine.add_note(channel, note);
                }
                
                let mut beat = 0.0f32;
                
                b.iter(|| {
                    beat = (beat + 1.0) % 256.0;
                    black_box(engine.process(black_box(beat)));
                });
            },
        );
    }
    
    group.finish();
}

/// Real-time safety benchmark - measure consistency
fn bench_realtime_consistency(c: &mut Criterion) {
    let mut group = c.benchmark_group("realtime");
    group.sample_size(1000); // More samples for consistency measurement
    
    group.bench_function("callback_128_samples", |b| {
        let mut mixer = Mixer::new(2);
        
        // Add 8 sine waves (typical track count)
        for i in 0..8 {
            let sine = SineWave::new(440.0 + i as f32 * 10.0, 0.1);
            mixer.add_source(Box::new(sine));
        }
        
        let mut output = vec![0.0f32; 128 * 2]; // 128 frames, stereo
        
        b.iter(|| {
            mixer.process(black_box(&mut output));
        });
    });
    
    group.finish();
}

criterion_group!(
    benches,
    bench_mixer_process,
    bench_sample_player,
    bench_transport_clock,
    bench_midi_engine,
    bench_realtime_consistency
);
criterion_main!(benches);
