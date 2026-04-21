//! version_control - Git LFS/DVC/lakeFS Integration
//!
//! Version control abstraction for audio files and projects.
//! Supports Git LFS, DVC, and lakeFS backends for large file versioning.
//!
//! Repositories:
//! - Git LFS: https://git-lfs.github.com
//! - DVC: https://dvc.org
//! - lakeFS: https://lakefs.io

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};
use std::path::Path;

/// Version control manager
pub struct VersionControl {
    handle: *mut c_void,
    backend: VcBackend,
}

/// Version control backend type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VcBackend {
    GitLfs,
    Dvc,
    LakeFs,
}

impl Default for VcBackend {
    fn default() -> Self {
        VcBackend::GitLfs
    }
}

/// File tracking status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TrackingStatus {
    Tracked,
    Untracked,
    Modified,
    Staged,
    Ignored,
}

impl Default for TrackingStatus {
    fn default() -> Self {
        TrackingStatus::Untracked
    }
}

/// LFS pointer file info
#[derive(Debug, Clone, PartialEq)]
pub struct LfsPointer {
    pub oid: String,
    pub size: u64,
    pub version: String,
}

impl Default for LfsPointer {
    fn default() -> Self {
        LfsPointer {
            oid: String::new(),
            size: 0,
            version: "https://git-lfs.github.com/spec/v1".to_string(),
        }
    }
}

/// Lock info
#[derive(Debug, Clone, PartialEq)]
pub struct LockInfo {
    pub id: String,
    pub path: String,
    pub owner: String,
    pub locked_at: String,
}

impl Default for LockInfo {
    fn default() -> Self {
        LockInfo {
            id: String::new(),
            path: String::new(),
            owner: String::new(),
            locked_at: String::new(),
        }
    }
}

/// Project snapshot
#[derive(Debug, Clone, PartialEq)]
pub struct ProjectSnapshot {
    pub id: String,
    pub message: String,
    pub timestamp: u64,
    pub author: String,
    pub files: Vec<String>,
}

impl Default for ProjectSnapshot {
    fn default() -> Self {
        ProjectSnapshot {
            id: String::new(),
            message: String::new(),
            timestamp: 0,
            author: String::new(),
            files: Vec::new(),
        }
    }
}

/// Storage configuration
#[derive(Debug, Clone, PartialEq)]
pub struct StorageConfig {
    pub remote_url: String,
    pub access_key: String,
    pub secret_key: String,
    pub region: String,
    pub bucket: String,
}

impl Default for StorageConfig {
    fn default() -> Self {
        StorageConfig {
            remote_url: String::new(),
            access_key: String::new(),
            secret_key: String::new(),
            region: "us-east-1".to_string(),
            bucket: String::new(),
        }
    }
}

/// DVC stage
#[derive(Debug, Clone, PartialEq)]
pub struct DvcStage {
    pub name: String,
    pub cmd: String,
    pub deps: Vec<String>,
    pub outs: Vec<String>,
}

impl Default for DvcStage {
    fn default() -> Self {
        DvcStage {
            name: String::new(),
            cmd: String::new(),
            deps: Vec::new(),
            outs: Vec::new(),
        }
    }
}

/// lakeFS repository
#[derive(Debug, Clone, PartialEq)]
pub struct LakeFsRepo {
    pub name: String,
    pub storage_namespace: String,
    pub default_branch: String,
}

impl Default for LakeFsRepo {
    fn default() -> Self {
        LakeFsRepo {
            name: String::new(),
            storage_namespace: String::new(),
            default_branch: "main".to_string(),
        }
    }
}

/// Version control availability status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VcStatus {
    Available,
    NotAvailable,
    Error(&'static str),
}

/// FFI interface to version control libraries
#[link(name = "daw_engine_ffi")]
extern "C" {
    fn vc_create(backend: c_int) -> *mut c_void;
    fn vc_destroy(handle: *mut c_void);
    fn vc_available(backend: c_int) -> c_int;
    fn vc_track_file(handle: *mut c_void, file_path: *const c_char) -> c_int;
    fn vc_untrack_file(handle: *mut c_void, file_path: *const c_char) -> c_int;
    fn vc_get_status(handle: *mut c_void, file_path: *const c_char) -> c_int;
    fn vc_read_pointer(handle: *mut c_void, pointer_path: *const c_char, 
                      oid: *mut c_char, oid_size: c_int, size: *mut u64) -> c_int;
    fn vc_write_pointer(handle: *mut c_void, file_path: *const c_char,
                       oid: *const c_char, size: u64) -> c_int;
    fn vc_lock(handle: *mut c_void, file_path: *const c_char) -> c_int;
    fn vc_unlock(handle: *mut c_void, file_path: *const c_char) -> c_int;
    fn vc_list_locks(handle: *mut c_void, locks_json: *mut c_char, buffer_size: c_int) -> c_int;
    fn vc_push(handle: *mut c_void, remote: *const c_char) -> c_int;
    fn vc_pull(handle: *mut c_void, remote: *const c_char) -> c_int;
    fn vc_fetch(handle: *mut c_void, remote: *const c_char) -> c_int;
    fn vc_create_snapshot(handle: *mut c_void, message: *const c_char, snapshot_id: *mut c_char, id_size: c_int) -> c_int;
    fn vc_list_snapshots(handle: *mut c_void, snapshots_json: *mut c_char, buffer_size: c_int) -> c_int;
    fn vc_restore_snapshot(handle: *mut c_void, snapshot_id: *const c_char) -> c_int;
    fn vc_config_storage(handle: *mut c_void, config_json: *const c_char) -> c_int;
}

impl VersionControl {
    /// Create new version control manager
    pub fn new(backend: VcBackend) -> Option<Self> {
        unsafe {
            let backend_id = match backend {
                VcBackend::GitLfs => 0,
                VcBackend::Dvc => 1,
                VcBackend::LakeFs => 2,
            };
            
            let handle = vc_create(backend_id);
            if handle.is_null() {
                None
            } else {
                Some(VersionControl { handle, backend })
            }
        }
    }

    /// Check if version control is available
    pub fn is_available(backend: VcBackend) -> bool {
        unsafe {
            let backend_id = match backend {
                VcBackend::GitLfs => 0,
                VcBackend::Dvc => 1,
                VcBackend::LakeFs => 2,
            };
            vc_available(backend_id) != 0
        }
    }

    /// Get availability status
    pub fn availability_status(backend: VcBackend) -> VcStatus {
        if Self::is_available(backend) {
            VcStatus::Available
        } else {
            VcStatus::NotAvailable
        }
    }

    /// Track a file
    pub fn track_file(&mut self, file_path: &str) -> Result<(), &'static str> {
        unsafe {
            let c_path = CString::new(file_path).map_err(|_| "Invalid file path")?;
            let result = vc_track_file(self.handle, c_path.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to track file")
            }
        }
    }

    /// Untrack a file
    pub fn untrack_file(&mut self, file_path: &str) -> Result<(), &'static str> {
        unsafe {
            let c_path = CString::new(file_path).map_err(|_| "Invalid file path")?;
            let result = vc_untrack_file(self.handle, c_path.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to untrack file")
            }
        }
    }

    /// Get file tracking status
    pub fn get_status(&self, file_path: &str) -> Result<TrackingStatus, &'static str> {
        unsafe {
            let c_path = CString::new(file_path).map_err(|_| "Invalid file path")?;
            let status = vc_get_status(self.handle, c_path.as_ptr());
            
            match status {
                0 => Ok(TrackingStatus::Untracked),
                1 => Ok(TrackingStatus::Tracked),
                2 => Ok(TrackingStatus::Modified),
                3 => Ok(TrackingStatus::Staged),
                4 => Ok(TrackingStatus::Ignored),
                _ => Err("Failed to get status"),
            }
        }
    }

    /// Read LFS pointer file
    pub fn read_pointer(&self, pointer_path: &str) -> Result<LfsPointer, &'static str> {
        unsafe {
            let c_path = CString::new(pointer_path).map_err(|_| "Invalid path")?;
            let mut oid_buffer = vec![0u8; 256];
            let mut size: u64 = 0;
            
            let result = vc_read_pointer(
                self.handle,
                c_path.as_ptr(),
                oid_buffer.as_mut_ptr() as *mut c_char,
                oid_buffer.len() as c_int,
                &mut size,
            );
            
            if result == 0 {
                let oid = CStr::from_ptr(oid_buffer.as_ptr() as *const c_char)
                    .to_str()
                    .map_err(|_| "Invalid OID")?;
                
                Ok(LfsPointer {
                    oid: oid.to_string(),
                    size,
                    version: "https://git-lfs.github.com/spec/v1".to_string(),
                })
            } else {
                Err("Failed to read pointer")
            }
        }
    }

    /// Write LFS pointer file
    pub fn write_pointer(&mut self, file_path: &str, pointer: &LfsPointer) -> Result<(), &'static str> {
        unsafe {
            let c_path = CString::new(file_path).map_err(|_| "Invalid file path")?;
            let c_oid = CString::new(pointer.oid.clone()).map_err(|_| "Invalid OID")?;
            
            let result = vc_write_pointer(self.handle, c_path.as_ptr(), c_oid.as_ptr(), pointer.size);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to write pointer")
            }
        }
    }

    /// Lock a file
    pub fn lock(&mut self, file_path: &str) -> Result<(), &'static str> {
        unsafe {
            let c_path = CString::new(file_path).map_err(|_| "Invalid file path")?;
            let result = vc_lock(self.handle, c_path.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to lock file")
            }
        }
    }

    /// Unlock a file
    pub fn unlock(&mut self, file_path: &str) -> Result<(), &'static str> {
        unsafe {
            let c_path = CString::new(file_path).map_err(|_| "Invalid file path")?;
            let result = vc_unlock(self.handle, c_path.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to unlock file")
            }
        }
    }

    /// Push to remote
    pub fn push(&mut self, remote: &str) -> Result<(), &'static str> {
        unsafe {
            let c_remote = CString::new(remote).map_err(|_| "Invalid remote")?;
            let result = vc_push(self.handle, c_remote.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to push")
            }
        }
    }

    /// Pull from remote
    pub fn pull(&mut self, remote: &str) -> Result<(), &'static str> {
        unsafe {
            let c_remote = CString::new(remote).map_err(|_| "Invalid remote")?;
            let result = vc_pull(self.handle, c_remote.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to pull")
            }
        }
    }

    /// Fetch from remote
    pub fn fetch(&mut self, remote: &str) -> Result<(), &'static str> {
        unsafe {
            let c_remote = CString::new(remote).map_err(|_| "Invalid remote")?;
            let result = vc_fetch(self.handle, c_remote.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to fetch")
            }
        }
    }

    /// Create project snapshot
    pub fn create_snapshot(&mut self, message: &str) -> Result<String, &'static str> {
        unsafe {
            let c_message = CString::new(message).map_err(|_| "Invalid message")?;
            let mut id_buffer = vec![0u8; 64];
            
            let result = vc_create_snapshot(
                self.handle,
                c_message.as_ptr(),
                id_buffer.as_mut_ptr() as *mut c_char,
                id_buffer.len() as c_int,
            );
            
            if result == 0 {
                let id = CStr::from_ptr(id_buffer.as_ptr() as *const c_char)
                    .to_str()
                    .map_err(|_| "Invalid snapshot ID")?;
                Ok(id.to_string())
            } else {
                Err("Failed to create snapshot")
            }
        }
    }

    /// Restore project snapshot
    pub fn restore_snapshot(&mut self, snapshot_id: &str) -> Result<(), &'static str> {
        unsafe {
            let c_id = CString::new(snapshot_id).map_err(|_| "Invalid snapshot ID")?;
            let result = vc_restore_snapshot(self.handle, c_id.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to restore snapshot")
            }
        }
    }

    /// Configure storage backend
    pub fn config_storage(&mut self, config: &StorageConfig) -> Result<(), &'static str> {
        unsafe {
            let config_json = format!(
                r#"{{"remote_url":"{}","access_key":"{}","secret_key":"{}","region":"{}","bucket":"{}"}}"#,
                config.remote_url, config.access_key, config.secret_key, 
                config.region, config.bucket
            );
            let c_json = CString::new(config_json).map_err(|_| "Invalid config")?;
            
            let result = vc_config_storage(self.handle, c_json.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to configure storage")
            }
        }
    }
}

impl Drop for VersionControl {
    fn drop(&mut self) {
        unsafe {
            vc_destroy(self.handle);
        }
    }
}

unsafe impl Send for VersionControl {}
unsafe impl Sync for VersionControl {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vc_availability() {
        let available = VersionControl::is_available(VcBackend::GitLfs);
        assert!(!available, "VersionControl should report not available (stub)");
    }

    #[test]
    fn test_vc_status() {
        let status = VersionControl::availability_status(VcBackend::GitLfs);
        match status {
            VcStatus::NotAvailable => (),
            VcStatus::Available => panic!("Should not be available with stub"),
            VcStatus::Error(_) => (),
        }
    }

    #[test]
    fn test_backend_default() {
        let backend = VcBackend::default();
        assert!(matches!(backend, VcBackend::GitLfs));
    }

    #[test]
    fn test_backend_variants() {
        let backends = [
            VcBackend::GitLfs,
            VcBackend::Dvc,
            VcBackend::LakeFs,
        ];
        
        for backend in &backends {
            // Just verify they exist
            let _: VcBackend = *backend;
        }
    }

    #[test]
    fn test_tracking_status_variants() {
        let statuses = [
            TrackingStatus::Tracked,
            TrackingStatus::Untracked,
            TrackingStatus::Modified,
            TrackingStatus::Staged,
            TrackingStatus::Ignored,
        ];
        
        for status in &statuses {
            let _: TrackingStatus = *status;
        }
    }

    #[test]
    fn test_lfs_pointer_default() {
        let ptr = LfsPointer::default();
        assert!(ptr.oid.is_empty());
        assert_eq!(ptr.size, 0);
        assert_eq!(ptr.version, "https://git-lfs.github.com/spec/v1");
    }

    #[test]
    fn test_lfs_pointer_custom() {
        let ptr = LfsPointer {
            oid: "sha256:abc123".to_string(),
            size: 1024000,
            version: "https://git-lfs.github.com/spec/v1".to_string(),
        };
        assert_eq!(ptr.oid, "sha256:abc123");
        assert_eq!(ptr.size, 1024000);
    }

    #[test]
    fn test_lock_info_default() {
        let lock = LockInfo::default();
        assert!(lock.id.is_empty());
        assert!(lock.path.is_empty());
        assert!(lock.owner.is_empty());
        assert!(lock.locked_at.is_empty());
    }

    #[test]
    fn test_lock_info_custom() {
        let lock = LockInfo {
            id: "lock_1".to_string(),
            path: "audio.wav".to_string(),
            owner: "user@example.com".to_string(),
            locked_at: "2026-04-06T12:00:00Z".to_string(),
        };
        assert_eq!(lock.id, "lock_1");
        assert_eq!(lock.path, "audio.wav");
        assert_eq!(lock.owner, "user@example.com");
    }

    #[test]
    fn test_project_snapshot_default() {
        let snap = ProjectSnapshot::default();
        assert!(snap.id.is_empty());
        assert!(snap.message.is_empty());
        assert_eq!(snap.timestamp, 0);
        assert!(snap.author.is_empty());
        assert!(snap.files.is_empty());
    }

    #[test]
    fn test_project_snapshot_custom() {
        let snap = ProjectSnapshot {
            id: "abc123".to_string(),
            message: "Initial commit".to_string(),
            timestamp: 1234567890,
            author: "user".to_string(),
            files: vec!["track1.wav".to_string(), "track2.wav".to_string()],
        };
        assert_eq!(snap.id, "abc123");
        assert_eq!(snap.message, "Initial commit");
        assert_eq!(snap.timestamp, 1234567890);
        assert_eq!(snap.author, "user");
        assert_eq!(snap.files.len(), 2);
    }

    #[test]
    fn test_storage_config_default() {
        let config = StorageConfig::default();
        assert!(config.remote_url.is_empty());
        assert!(config.access_key.is_empty());
        assert!(config.secret_key.is_empty());
        assert_eq!(config.region, "us-east-1");
        assert!(config.bucket.is_empty());
    }

    #[test]
    fn test_storage_config_custom() {
        let config = StorageConfig {
            remote_url: "s3://mybucket".to_string(),
            access_key: "AKIAIOSFODNN7EXAMPLE".to_string(),
            secret_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY".to_string(),
            region: "eu-west-1".to_string(),
            bucket: "mybucket".to_string(),
        };
        assert_eq!(config.remote_url, "s3://mybucket");
        assert_eq!(config.region, "eu-west-1");
        assert_eq!(config.bucket, "mybucket");
    }

    #[test]
    fn test_dvc_stage_default() {
        let stage = DvcStage::default();
        assert!(stage.name.is_empty());
        assert!(stage.cmd.is_empty());
        assert!(stage.deps.is_empty());
        assert!(stage.outs.is_empty());
    }

    #[test]
    fn test_dvc_stage_custom() {
        let stage = DvcStage {
            name: "process".to_string(),
            cmd: "python process.py".to_string(),
            deps: vec!["process.py".to_string(), "data.raw".to_string()],
            outs: vec!["data.processed".to_string()],
        };
        assert_eq!(stage.name, "process");
        assert_eq!(stage.cmd, "python process.py");
        assert_eq!(stage.deps.len(), 2);
        assert_eq!(stage.outs.len(), 1);
    }

    #[test]
    fn test_lakefs_repo_default() {
        let repo = LakeFsRepo::default();
        assert!(repo.name.is_empty());
        assert!(repo.storage_namespace.is_empty());
        assert_eq!(repo.default_branch, "main");
    }

    #[test]
    fn test_lakefs_repo_custom() {
        let repo = LakeFsRepo {
            name: "my-repo".to_string(),
            storage_namespace: "s3://bucket".to_string(),
            default_branch: "master".to_string(),
        };
        assert_eq!(repo.name, "my-repo");
        assert_eq!(repo.storage_namespace, "s3://bucket");
        assert_eq!(repo.default_branch, "master");
    }
}
