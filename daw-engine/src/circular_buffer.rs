//! Lock-free SPSC Circular Buffer for Audio Streaming
//!
//! Single-producer (background read thread), single-consumer (audio thread)
//! Uses atomic indices for lock-free operation on the hot path (audio thread)

use std::sync::atomic::{AtomicUsize, Ordering};

/// Lock-free SPSC circular buffer for f32 audio samples
pub struct CircularBuffer {
    buffer: Vec<f32>,
    write_idx: AtomicUsize,
    read_idx: AtomicUsize,
    capacity: usize,
}

impl CircularBuffer {
    /// Create a new circular buffer with capacity (must be power of 2 for efficient masking)
    pub fn new(capacity: usize) -> Self {
        // Round up to next power of 2 for efficient masking
        let capacity = if capacity.is_power_of_two() {
            capacity
        } else {
            capacity.next_power_of_two()
        };
        
        Self {
            buffer: vec![0.0f32; capacity],
            write_idx: AtomicUsize::new(0),
            read_idx: AtomicUsize::new(0),
            capacity,
        }
    }
    
    /// Get buffer capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }
    
    /// Write samples to buffer, returns number of samples written
    pub fn write(&mut self, data: &[f32]) -> usize {
        let write_idx = self.write_idx.load(Ordering::Relaxed);
        let read_idx = self.read_idx.load(Ordering::Acquire);
        
        let available = self.available_write_internal(write_idx, read_idx);
        if available == 0 {
            return 0;
        }
        
        let to_write = data.len().min(available);
        let mask = self.capacity - 1;
        
        // Write in two parts if wrapping around
        let write_pos = write_idx & mask;
        let first_part = to_write.min(self.capacity - write_pos);
        
        // First part: write_pos to end of buffer
        self.buffer[write_pos..write_pos + first_part]
            .copy_from_slice(&data[..first_part]);
        
        // Second part: start of buffer if needed
        if to_write > first_part {
            let second_part = to_write - first_part;
            self.buffer[..second_part]
                .copy_from_slice(&data[first_part..to_write]);
        }
        
        // Update write index (Release ordering to ensure writes are visible)
        self.write_idx.store(write_idx + to_write, Ordering::Release);
        
        to_write
    }
    
    /// Read samples from buffer, returns number of samples read
    pub fn read(&self, out: &mut [f32]) -> usize {
        let read_idx = self.read_idx.load(Ordering::Relaxed);
        let write_idx = self.write_idx.load(Ordering::Acquire);
        
        let available = self.available_read_internal(write_idx, read_idx);
        if available == 0 {
            return 0;
        }
        
        let to_read = out.len().min(available);
        let mask = self.capacity - 1;
        
        // Read in two parts if wrapping around
        let read_pos = read_idx & mask;
        let first_part = to_read.min(self.capacity - read_pos);
        
        // First part: read_pos to end of buffer
        out[..first_part].copy_from_slice(&self.buffer[read_pos..read_pos + first_part]);
        
        // Second part: start of buffer if needed
        if to_read > first_part {
            let second_part = to_read - first_part;
            out[first_part..to_read].copy_from_slice(&self.buffer[..second_part]);
        }
        
        // Update read index (Release ordering to signal consumption)
        self.read_idx.store(read_idx + to_read, Ordering::Release);
        
        to_read
    }
    
    /// Get number of samples available to read (for consumer)
    pub fn available_read(&self) -> usize {
        let write_idx = self.write_idx.load(Ordering::Acquire);
        let read_idx = self.read_idx.load(Ordering::Relaxed);
        self.available_read_internal(write_idx, read_idx)
    }
    
    /// Get number of samples that can be written (for producer)
    pub fn available_write(&self) -> usize {
        let write_idx = self.write_idx.load(Ordering::Relaxed);
        let read_idx = self.read_idx.load(Ordering::Acquire);
        self.available_write_internal(write_idx, read_idx)
    }
    
    /// Internal calculation for available read space
    fn available_read_internal(&self, write_idx: usize, read_idx: usize) -> usize {
        write_idx.wrapping_sub(read_idx)
    }
    
    /// Internal calculation for available write space
    fn available_write_internal(&self, write_idx: usize, read_idx: usize) -> usize {
        self.capacity - self.available_read_internal(write_idx, read_idx)
    }
    
    /// Clear the buffer (reset indices)
    pub fn clear(&self) {
        self.write_idx.store(0, Ordering::Relaxed);
        self.read_idx.store(0, Ordering::Relaxed);
    }
    
    /// Check if buffer is empty
    pub fn is_empty(&self) -> bool {
        self.available_read() == 0
    }
    
    /// Peek at samples without consuming them (for inspection)
    pub fn peek(&self, out: &mut [f32]) -> usize {
        let read_idx = self.read_idx.load(Ordering::Relaxed);
        let write_idx = self.write_idx.load(Ordering::Acquire);
        
        let available = self.available_read_internal(write_idx, read_idx);
        if available == 0 {
            return 0;
        }
        
        let to_peek = out.len().min(available);
        let mask = self.capacity - 1;
        let read_pos = read_idx & mask;
        let first_part = to_peek.min(self.capacity - read_pos);
        
        out[..first_part].copy_from_slice(&self.buffer[read_pos..read_pos + first_part]);
        
        if to_peek > first_part {
            let second_part = to_peek - first_part;
            out[first_part..to_peek].copy_from_slice(&self.buffer[..second_part]);
        }
        
        to_peek
    }
}

unsafe impl Send for CircularBuffer {}
unsafe impl Sync for CircularBuffer {}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_circular_buffer_creation() {
        let buf = CircularBuffer::new(1024);
        assert_eq!(buf.capacity(), 1024);
        assert_eq!(buf.available_read(), 0);
        assert_eq!(buf.available_write(), 1024);
        assert!(buf.is_empty());
    }
    
    #[test]
    fn test_capacity_rounds_to_power_of_2() {
        let buf = CircularBuffer::new(1000);
        assert_eq!(buf.capacity(), 1024); // Next power of 2
    }
    
    #[test]
    fn test_write_and_read() {
        let mut buf = CircularBuffer::new(1024);
        
        let input = vec![1.0f32, 2.0, 3.0, 4.0, 5.0];
        let written = buf.write(&input);
        assert_eq!(written, 5);
        assert_eq!(buf.available_read(), 5);
        
        let mut output = vec![0.0f32; 5];
        let read = buf.read(&mut output);
        assert_eq!(read, 5);
        assert_eq!(output, input);
        assert!(buf.is_empty());
    }
    
    #[test]
    fn test_wraparound() {
        let mut buf = CircularBuffer::new(16);
        
        // Fill buffer
        let data = vec![1.0f32; 16];
        buf.write(&data);
        
        // Consume 8 samples
        let mut out = vec![0.0f32; 8];
        buf.read(&mut out);
        
        // Write 8 more (should wrap)
        let data2 = vec![2.0f32; 8];
        buf.write(&data2);
        
        // Read all 16
        let mut out2 = vec![0.0f32; 16];
        buf.read(&mut out2);
        
        // First 8 should be 1.0, last 8 should be 2.0
        assert!(out2[..8].iter().all(|&s| s == 1.0));
        assert!(out2[8..].iter().all(|&s| s == 2.0));
    }
    
    #[test]
    fn test_partial_write_when_full() {
        let mut buf = CircularBuffer::new(8);
        
        // Fill completely
        buf.write(&vec![1.0f32; 8]);
        
        // Try to write more
        let written = buf.write(&vec![2.0f32; 4]);
        assert_eq!(written, 0); // Can't write anything
        
        // Read some
        let mut out = vec![0.0f32; 4];
        buf.read(&mut out);
        
        // Now we can write 4
        let written = buf.write(&vec![2.0f32; 4]);
        assert_eq!(written, 4);
    }
    
    #[test]
    fn test_partial_read_when_empty() {
        let mut buf = CircularBuffer::new(16);
        
        let mut out = vec![0.0f32; 8];
        let read = buf.read(&mut out);
        assert_eq!(read, 0);
    }
    
    #[test]
    fn test_clear() {
        let mut buf = CircularBuffer::new(16);
        buf.write(&vec![1.0f32; 8]);
        
        buf.clear();
        
        assert!(buf.is_empty());
        assert_eq!(buf.available_read(), 0);
        assert_eq!(buf.available_write(), 16);
    }
    
    #[test]
    fn test_peek_does_not_consume() {
        let mut buf = CircularBuffer::new(16);
        buf.write(&vec![1.0f32, 2.0, 3.0, 4.0]);
        
        let mut peek_buf = vec![0.0f32; 2];
        let peeked = buf.peek(&mut peek_buf);
        assert_eq!(peeked, 2);
        assert_eq!(peek_buf, vec![1.0, 2.0]);
        
        // Buffer should still have 4 available
        assert_eq!(buf.available_read(), 4);
    }
    
    #[test]
    fn test_multiple_write_read_cycles() {
        let mut buf = CircularBuffer::new(64);
        
        for i in 0..10 {
            let data = vec![i as f32; 8];
            buf.write(&data);
            
            let mut out = vec![0.0f32; 8];
            buf.read(&mut out);
            
            assert_eq!(out, data);
        }
    }
    
    #[test]
    fn test_concurrent_single_threaded() {
        // This test simulates what happens with proper sequencing
        let mut buf = CircularBuffer::new(256);
        
        // Simulate producer
        let producer_data: Vec<f32> = (0..100).map(|i| i as f32).collect();
        
        // Write in chunks
        let mut written = 0;
        while written < producer_data.len() {
            let to_write = (producer_data.len() - written).min(16);
            let n = buf.write(&producer_data[written..written + to_write]);
            written += n;
        }
        
        // Simulate consumer
        let mut consumer_data = Vec::new();
        while consumer_data.len() < 100 {
            let mut chunk = vec![0.0f32; 16];
            let n = buf.read(&mut chunk);
            if n == 0 {
                break;
            }
            consumer_data.extend_from_slice(&chunk[..n]);
        }
        
        assert_eq!(consumer_data.len(), 100);
        assert_eq!(consumer_data, producer_data);
    }
}
