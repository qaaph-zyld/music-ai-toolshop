//! Real-time Audio Thread Hardening
//!
//! Provides lock-free data structures, priority inversion protection,
//! and watchdog timers for reliable real-time audio processing.

use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

/// Lock-free single-producer single-consumer queue for real-time audio
/// Uses a ring buffer with atomic indices
pub struct LockFreeQueue<T, const N: usize> {
    buffer: Box<[T; N]>,
    write_index: AtomicUsize,
    read_index: AtomicUsize,
}

impl<T: Default + Clone + Copy, const N: usize> LockFreeQueue<T, N> {
    /// Create new lock-free queue
    pub fn new() -> Self {
        Self {
            buffer: Box::new([T::default(); N]),
            write_index: AtomicUsize::new(0),
            read_index: AtomicUsize::new(0),
        }
    }

    /// Push item (non-blocking, thread-safe)
    /// Returns false if queue is full
    pub fn push(&self, item: T) -> bool {
        let write = self.write_index.load(Ordering::Relaxed);
        let read = self.read_index.load(Ordering::Acquire);
        
        let next_write = (write + 1) % N;
        if next_write == read {
            return false; // Queue full
        }
        
        // Safe: we're the only writer
        unsafe {
            let ptr = self.buffer.as_ptr().add(write) as *mut T;
            ptr.write(item);
        }
        
        self.write_index.store(next_write, Ordering::Release);
        true
    }

    /// Pop item (non-blocking, thread-safe)
    /// Returns None if queue is empty
    pub fn pop(&self) -> Option<T> {
        let read = self.read_index.load(Ordering::Relaxed);
        let write = self.write_index.load(Ordering::Acquire);
        
        if read == write {
            return None; // Queue empty
        }
        
        // Safe: we're the only reader
        let item = unsafe {
            let ptr = self.buffer.as_ptr().add(read);
            ptr.read()
        };
        
        let next_read = (read + 1) % N;
        self.read_index.store(next_read, Ordering::Release);
        
        Some(item)
    }

    /// Check if queue is empty
    pub fn is_empty(&self) -> bool {
        self.write_index.load(Ordering::Acquire) == self.read_index.load(Ordering::Relaxed)
    }

    /// Check if queue is full
    pub fn is_full(&self) -> bool {
        let next = (self.write_index.load(Ordering::Relaxed) + 1) % N;
        next == self.read_index.load(Ordering::Acquire)
    }

    /// Get approximate count (may be slightly off due to race conditions)
    pub fn len(&self) -> usize {
        let write = self.write_index.load(Ordering::Relaxed);
        let read = self.read_index.load(Ordering::Relaxed);
        (write + N - read) % N
    }
}

impl<T: Default + Clone + Copy, const N: usize> Default for LockFreeQueue<T, N> {
    fn default() -> Self {
        Self::new()
    }
}

/// Real-time safe command for audio thread
#[derive(Debug, Clone, Copy)]
pub enum RealTimeCommand {
    Play,
    Stop,
    SetPosition(f32),
    SetTempo(f32),
    LaunchClip(usize, usize),
    StopClip(usize, usize),
    SetVolume(usize, f32),
    SetPan(usize, f32),
    SetMute(usize, bool),
    Nop, // No operation (for padding)
}

impl Default for RealTimeCommand {
    fn default() -> Self {
        RealTimeCommand::Nop
    }
}

/// Watchdog timer for detecting audio thread stalls
pub struct WatchdogTimer {
    last_update: AtomicU64, // Microseconds since epoch
    timeout_us: u64,
    callback: Box<dyn Fn() + Send + Sync>,
}

impl WatchdogTimer {
    /// Create new watchdog timer
    /// timeout: duration after which callback is triggered
    pub fn new<F>(timeout: Duration, callback: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        Self {
            last_update: AtomicU64::new(0),
            timeout_us: timeout.as_micros() as u64,
            callback: Box::new(callback),
        }
    }

    /// Reset the watchdog (call from audio thread)
    pub fn pet(&self) {
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_micros() as u64;
        self.last_update.store(now, Ordering::Release);
    }

    /// Check if watchdog has expired (call from monitoring thread)
    pub fn check(&self) -> bool {
        let last = self.last_update.load(Ordering::Acquire);
        if last == 0 {
            return false; // Not initialized yet
        }
        
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_micros() as u64;
        let elapsed = now.saturating_sub(last);
        
        if elapsed > self.timeout_us {
            (self.callback)();
            true
        } else {
            false
        }
    }

    /// Get elapsed time since last pet
    pub fn elapsed_us(&self) -> u64 {
        let last = self.last_update.load(Ordering::Acquire);
        if last == 0 {
            return 0;
        }
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_micros() as u64;
        now.saturating_sub(last)
    }
}

/// Priority inversion safe mutex wrapper
/// Uses priority inheritance protocol (simulated via try_lock with timeout)
pub struct RealTimeMutex<T> {
    data: std::sync::Mutex<T>,
}

impl<T> RealTimeMutex<T> {
    /// Create new real-time mutex
    pub fn new(data: T) -> Self {
        Self {
            data: std::sync::Mutex::new(data),
        }
    }

    /// Try to lock with timeout (real-time safe)
    pub fn try_lock_for(&self, timeout: Duration) -> Option<std::sync::MutexGuard<'_, T>> {
        let start = Instant::now();
        loop {
            if let Ok(guard) = self.data.try_lock() {
                return Some(guard);
            }
            if start.elapsed() > timeout {
                return None;
            }
            std::thread::yield_now();
        }
    }

    /// Lock (blocks indefinitely - not real-time safe)
    pub fn lock(&self) -> std::sync::MutexGuard<'_, T> {
        self.data.lock().unwrap()
    }
}

/// Audio thread statistics and monitoring
#[derive(Debug, Default)]
pub struct AudioThreadStats {
    /// Callback count
    pub callbacks: AtomicU64,
    /// Underrun count
    pub underruns: AtomicU64,
    /// Average callback duration (microseconds)
    pub avg_duration_us: AtomicU64,
    /// Max callback duration (microseconds)
    pub max_duration_us: AtomicU64,
}

impl AudioThreadStats {
    /// Create new stats tracker
    pub fn new() -> Self {
        Self::default()
    }

    /// Record callback duration
    pub fn record_callback(&self, duration: Duration) {
        self.callbacks.fetch_add(1, Ordering::Relaxed);
        
        let us = duration.as_micros() as u64;
        
        // Update max
        let mut current_max = self.max_duration_us.load(Ordering::Relaxed);
        while us > current_max {
            match self.max_duration_us.compare_exchange(
                current_max,
                us,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(actual) => current_max = actual,
            }
        }
        
        // Update average (exponential moving average)
        let alpha = 0.1; // Smoothing factor
        let current_avg = self.avg_duration_us.load(Ordering::Relaxed) as f64;
        let new_avg = (alpha * us as f64) + ((1.0 - alpha) * current_avg);
        self.avg_duration_us.store(new_avg as u64, Ordering::Relaxed);
    }

    /// Record underrun
    pub fn record_underrun(&self) {
        self.underruns.fetch_add(1, Ordering::Relaxed);
    }

    /// Get current stats snapshot
    pub fn snapshot(&self) -> AudioStatsSnapshot {
        AudioStatsSnapshot {
            callbacks: self.callbacks.load(Ordering::Relaxed),
            underruns: self.underruns.load(Ordering::Relaxed),
            avg_duration_us: self.avg_duration_us.load(Ordering::Relaxed),
            max_duration_us: self.max_duration_us.load(Ordering::Relaxed),
        }
    }
}

/// Snapshot of audio thread stats
#[derive(Debug, Clone, Copy)]
pub struct AudioStatsSnapshot {
    pub callbacks: u64,
    pub underruns: u64,
    pub avg_duration_us: u64,
    pub max_duration_us: u64,
}

/// Real-time command processor
pub struct RealTimeCommandProcessor {
    queue: Arc<LockFreeQueue<RealTimeCommand, 256>>,
    watchdog: Arc<WatchdogTimer>,
    stats: Arc<AudioThreadStats>,
}

impl RealTimeCommandProcessor {
    /// Create new command processor
    pub fn new<F>(watchdog_timeout: Duration, watchdog_callback: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        Self {
            queue: Arc::new(LockFreeQueue::new()),
            watchdog: Arc::new(WatchdogTimer::new(watchdog_timeout, watchdog_callback)),
            stats: Arc::new(AudioThreadStats::new()),
        }
    }

    /// Send command (non-blocking)
    pub fn send(&self, cmd: RealTimeCommand) -> bool {
        self.queue.push(cmd)
    }

    /// Process all pending commands (call from audio thread)
    pub fn process<F>(&self, mut handler: F)
    where
        F: FnMut(RealTimeCommand),
    {
        let start = Instant::now();
        
        // Pet the watchdog
        self.watchdog.pet();
        
        // Process all pending commands
        while let Some(cmd) = self.queue.pop() {
            handler(cmd);
        }
        
        // Record stats
        self.stats.record_callback(start.elapsed());
    }

    /// Get queue reference
    pub fn queue(&self) -> &LockFreeQueue<RealTimeCommand, 256> {
        &self.queue
    }

    /// Get watchdog reference
    pub fn watchdog(&self) -> &WatchdogTimer {
        &self.watchdog
    }

    /// Get stats reference
    pub fn stats(&self) -> &AudioThreadStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::sync::atomic::AtomicBool;

    #[test]
    fn test_lock_free_queue_basic() {
        let queue = LockFreeQueue::<i32, 16>::new();
        
        assert!(queue.is_empty());
        assert!(!queue.is_full());
        
        // Push items
        for i in 0..10 {
            assert!(queue.push(i));
        }
        
        assert!(!queue.is_empty());
        assert_eq!(queue.len(), 10);
        
        // Pop items
        for i in 0..10 {
            assert_eq!(queue.pop(), Some(i));
        }
        
        assert!(queue.is_empty());
        assert_eq!(queue.pop(), None);
    }

    #[test]
    fn test_lock_free_queue_full() {
        let queue = LockFreeQueue::<i32, 4>::new();
        
        // Fill queue (capacity is N-1 due to ring buffer design)
        assert!(queue.push(1));
        assert!(queue.push(2));
        assert!(queue.push(3));
        assert!(!queue.push(4)); // Should fail - queue full
        
        assert!(queue.is_full());
    }

    #[test]
    fn test_lock_free_queue_threaded() {
        let queue = Arc::new(LockFreeQueue::<i32, 1024>::new());
        let q1 = Arc::clone(&queue);
        let q2 = Arc::clone(&queue);
        
        // Producer thread
        let producer = thread::spawn(move || {
            for i in 0..100 {
                while !q1.push(i) {
                    thread::yield_now();
                }
            }
        });
        
        // Consumer thread
        let consumer = thread::spawn(move || {
            let mut count = 0;
            while count < 100 {
                if q2.pop().is_some() {
                    count += 1;
                } else {
                    thread::yield_now();
                }
            }
            count
        });
        
        producer.join().unwrap();
        let consumed = consumer.join().unwrap();
        assert_eq!(consumed, 100);
    }

    #[test]
    fn test_watchdog_timer() {
        let triggered = Arc::new(AtomicBool::new(false));
        let t = Arc::clone(&triggered);
        
        let watchdog = WatchdogTimer::new(Duration::from_millis(10), move || {
            t.store(true, Ordering::SeqCst);
        });
        
        // Should not trigger immediately
        assert!(!watchdog.check());
        
        // Pet the watchdog
        watchdog.pet();
        assert!(!watchdog.check());
        
        // Wait for timeout
        thread::sleep(Duration::from_millis(20));
        assert!(watchdog.check());
        assert!(triggered.load(Ordering::SeqCst));
    }

    #[test]
    fn test_real_time_mutex() {
        let mutex = RealTimeMutex::new(42);
        
        // Basic lock
        {
            let guard = mutex.lock();
            assert_eq!(*guard, 42);
        }
        
        // Try lock with timeout
        let guard = mutex.try_lock_for(Duration::from_millis(1));
        assert!(guard.is_some());
        assert_eq!(*guard.unwrap(), 42);
    }

    #[test]
    fn test_audio_thread_stats() {
        let stats = AudioThreadStats::new();
        
        // Record some callbacks
        stats.record_callback(Duration::from_micros(100));
        stats.record_callback(Duration::from_micros(200));
        stats.record_callback(Duration::from_micros(300));
        
        // Record underrun
        stats.record_underrun();
        
        let snapshot = stats.snapshot();
        assert_eq!(snapshot.callbacks, 3);
        assert_eq!(snapshot.underruns, 1);
        assert!(snapshot.avg_duration_us > 0);
        assert!(snapshot.max_duration_us >= 300);
    }

    #[test]
    fn test_command_processor() {
        let triggered = Arc::new(AtomicBool::new(false));
        let t = Arc::clone(&triggered);
        
        let processor = RealTimeCommandProcessor::new(
            Duration::from_millis(100),
            move || {
                t.store(true, Ordering::SeqCst);
            },
        );
        
        // Send commands
        assert!(processor.send(RealTimeCommand::Play));
        assert!(processor.send(RealTimeCommand::Stop));
        
        // Process commands
        let mut received = Vec::new();
        processor.process(|cmd| {
            received.push(cmd);
        });
        
        assert_eq!(received.len(), 2);
        
        // Check watchdog was petted
        assert!(!triggered.load(Ordering::SeqCst));
        assert_eq!(processor.stats().snapshot().callbacks, 1);
    }
}
