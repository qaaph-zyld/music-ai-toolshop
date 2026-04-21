//! Memory pool allocators for zero audio-thread allocations
//!
//! Provides pre-allocated object pools to eliminate runtime allocations
//! in the real-time audio processing thread.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

/// Generic object pool for reusable objects
pub struct ObjectPool<T> {
    available: VecDeque<T>,
    capacity: usize,
}

/// Pre-allocated audio buffer pool
pub struct SampleBufferPool {
    buffers: VecDeque<Vec<f32>>,
    buffer_size: usize,
    capacity: usize,
}

impl<T> ObjectPool<T> {
    /// Create a new object pool with the specified capacity
    pub fn new<F>(capacity: usize, factory: F) -> Self
    where
        F: Fn() -> T,
    {
        let mut available = VecDeque::with_capacity(capacity);
        for _ in 0..capacity {
            available.push_back(factory());
        }

        Self {
            available,
            capacity,
        }
    }

    /// Acquire an object from the pool
    /// Returns None if pool is exhausted
    pub fn acquire(&mut self) -> Option<T> {
        self.available.pop_front()
    }

    /// Release an object back to the pool
    pub fn release(&mut self, obj: T) {
        if self.available.len() < self.capacity {
            self.available.push_back(obj);
        }
        // If at capacity, object is dropped
    }

    /// Get the number of available objects
    pub fn available_count(&self) -> usize {
        self.available.len()
    }

    /// Get the pool capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Check if the pool is exhausted
    pub fn is_exhausted(&self) -> bool {
        self.available.is_empty()
    }
}

impl SampleBufferPool {
    /// Create a new sample buffer pool
    pub fn new(buffer_size: usize, capacity: usize) -> Self {
        let mut buffers = VecDeque::with_capacity(capacity);
        for _ in 0..capacity {
            buffers.push_back(vec![0.0f32; buffer_size]);
        }

        Self {
            buffers,
            buffer_size,
            capacity,
        }
    }

    /// Acquire a buffer from the pool
    pub fn acquire(&mut self) -> Option<Vec<f32>> {
        let mut buffer = self.buffers.pop_front()?;
        // Clear the buffer before returning
        buffer.fill(0.0f32);
        Some(buffer)
    }

    /// Release a buffer back to the pool
    pub fn release(&mut self, mut buffer: Vec<f32>) {
        if self.buffers.len() < self.capacity && buffer.len() == self.buffer_size {
            buffer.fill(0.0f32);
            self.buffers.push_back(buffer);
        }
        // If wrong size or at capacity, buffer is dropped
    }

    /// Get available buffer count
    pub fn available_count(&self) -> usize {
        self.buffers.len()
    }

    /// Get pool capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Get buffer size
    pub fn buffer_size(&self) -> usize {
        self.buffer_size
    }
}

/// Thread-safe object pool using Arc<Mutex<>>
pub struct SharedObjectPool<T> {
    inner: Arc<Mutex<ObjectPool<T>>>,
}

impl<T: Send> SharedObjectPool<T> {
    /// Create a new shared object pool
    pub fn new<F>(capacity: usize, factory: F) -> Self
    where
        F: Fn() -> T,
    {
        Self {
            inner: Arc::new(Mutex::new(ObjectPool::new(capacity, factory))),
        }
    }

    /// Acquire an object from the pool
    pub fn acquire(&self) -> Option<T> {
        self.inner.lock().ok()?.acquire()
    }

    /// Release an object back to the pool
    pub fn release(&self, obj: T) {
        if let Ok(mut pool) = self.inner.lock() {
            pool.release(obj);
        }
    }

    /// Get available count
    pub fn available_count(&self) -> usize {
        self.inner.lock().map(|p| p.available_count()).unwrap_or(0)
    }
}

impl<T> Clone for SharedObjectPool<T> {
    fn clone(&self) -> Self {
        Self {
            inner: Arc::clone(&self.inner),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_object_pool_creation() {
        let pool = ObjectPool::new(5, || 42);
        assert_eq!(pool.capacity(), 5);
        assert_eq!(pool.available_count(), 5);
        assert!(!pool.is_exhausted());
    }

    #[test]
    fn test_object_pool_acquire() {
        let mut pool = ObjectPool::new(3, || 42);
        let obj = pool.acquire().unwrap();
        assert_eq!(obj, 42);
        assert_eq!(pool.available_count(), 2);
    }

    #[test]
    fn test_object_pool_release() {
        let mut pool = ObjectPool::new(3, || 0);
        let obj = pool.acquire().unwrap();
        pool.release(obj);
        assert_eq!(pool.available_count(), 3);
    }

    #[test]
    fn test_object_pool_exhaustion() {
        let mut pool = ObjectPool::new(2, || 42);
        let _ = pool.acquire();
        let _ = pool.acquire();
        assert!(pool.is_exhausted());
        assert!(pool.acquire().is_none());
    }

    #[test]
    fn test_sample_buffer_pool() {
        let mut pool = SampleBufferPool::new(1024, 4);
        assert_eq!(pool.buffer_size(), 1024);
        assert_eq!(pool.capacity(), 4);
        assert_eq!(pool.available_count(), 4);

        let buffer = pool.acquire().unwrap();
        assert_eq!(buffer.len(), 1024);
        assert_eq!(pool.available_count(), 3);

        pool.release(buffer);
        assert_eq!(pool.available_count(), 4);
    }

    #[test]
    fn test_sample_buffer_cleared_on_acquire() {
        let mut pool = SampleBufferPool::new(4, 2);
        let mut buffer = pool.acquire().unwrap();
        buffer[0] = 1.0;
        buffer[1] = 2.0;
        pool.release(buffer);

        let buffer = pool.acquire().unwrap();
        assert_eq!(buffer[0], 0.0);
        assert_eq!(buffer[1], 0.0);
    }

    #[test]
    fn test_shared_pool_thread_safety() {
        let pool = SharedObjectPool::new(5, || 42);
        let pool2 = pool.clone();

        let obj = pool.acquire().unwrap();
        assert_eq!(obj, 42);

        pool2.release(obj);
        assert_eq!(pool.available_count(), 5);
    }
}
