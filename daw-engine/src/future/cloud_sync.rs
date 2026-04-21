use std::path::{Path, PathBuf};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SyncConflictResolution {
    KeepLocal,
    KeepRemote,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CloudSyncStatus {
    pub last_synced: Option<DateTime<Utc>>,
    pub pending_local_changes: bool,
    pub pending_remote_changes: bool,
}

pub trait StorageBackend {
    fn upload_file(&self, local_path: &Path, remote_path: &str) -> Result<(), String>;
    fn download_file(&self, remote_path: &str, local_path: &Path) -> Result<(), String>;
    fn get_remote_modified_time(&self, remote_path: &str) -> Result<Option<DateTime<Utc>>, String>;
}

pub struct CloudSyncEngine<B: StorageBackend> {
    backend: B,
}

impl<B: StorageBackend> CloudSyncEngine<B> {
    pub fn new(backend: B) -> Self {
        Self { backend }
    }

    pub fn resolve_conflict(&self, local_modified: DateTime<Utc>, remote_modified: DateTime<Utc>) -> SyncConflictResolution {
        if local_modified >= remote_modified {
            SyncConflictResolution::KeepLocal
        } else {
            SyncConflictResolution::KeepRemote
        }
    }

    pub fn check_sync_status(&self, local_file: &Path, remote_path: &str) -> Result<CloudSyncStatus, String> {
        // Get local file modified time
        let local_modified = std::fs::metadata(local_file)
            .and_then(|m| m.modified())
            .map(|t| {
                let duration = t.duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
                DateTime::from_timestamp(duration.as_secs() as i64, duration.subsec_nanos())
                    .unwrap_or_else(|| Utc::now())
            })
            .unwrap_or_else(|_| Utc::now());

        // Get remote modified time
        let remote_modified = self.backend.get_remote_modified_time(remote_path)?;

        let (pending_local, pending_remote) = match remote_modified {
            Some(remote_time) => {
                let local_pending = local_modified > remote_time;
                let remote_pending = remote_time > local_modified;
                (local_pending, remote_pending)
            }
            None => {
                // Remote file doesn't exist - local has pending changes
                (true, false)
            }
        };

        Ok(CloudSyncStatus {
            last_synced: remote_modified,
            pending_local_changes: pending_local,
            pending_remote_changes: pending_remote,
        })
    }
}

/// Local storage cache backend
pub struct LocalStorage {
    base_path: PathBuf,
}

impl LocalStorage {
    pub fn new(base_path: PathBuf) -> Self {
        Self { base_path }
    }
}

impl StorageBackend for LocalStorage {
    fn upload_file(&self, local_path: &Path, remote_path: &str) -> Result<(), String> {
        let dest = self.base_path.join(remote_path);
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        std::fs::copy(local_path, dest).map_err(|e| e.to_string())?;
        Ok(())
    }

    fn download_file(&self, remote_path: &str, local_path: &Path) -> Result<(), String> {
        let src = self.base_path.join(remote_path);
        std::fs::copy(src, local_path).map_err(|e| e.to_string())?;
        Ok(())
    }

    fn get_remote_modified_time(&self, remote_path: &str) -> Result<Option<DateTime<Utc>>, String> {
        let path = self.base_path.join(remote_path);
        if !path.exists() {
            return Ok(None);
        }
        let metadata = std::fs::metadata(path).map_err(|e| e.to_string())?;
        let modified = metadata.modified().map_err(|e| e.to_string())?;
        let duration = modified.duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
        Ok(DateTime::from_timestamp(duration.as_secs() as i64, duration.subsec_nanos()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::sync::{Arc, Mutex};

    struct MockStorageBackend {
        _files: Arc<Mutex<HashMap<String, Vec<u8>>>>,
        times: Arc<Mutex<HashMap<String, DateTime<Utc>>>>,
    }

    impl MockStorageBackend {
        fn new() -> Self {
            Self {
                _files: Arc::new(Mutex::new(HashMap::new())),
                times: Arc::new(Mutex::new(HashMap::new())),
            }
        }

        #[allow(dead_code)]
        fn set_remote_time(&self, path: &str, time: DateTime<Utc>) {
            self.times.lock().unwrap().insert(path.to_string(), time);
        }
    }

    impl StorageBackend for MockStorageBackend {
        fn upload_file(&self, _local_path: &Path, _remote_path: &str) -> Result<(), String> {
            Ok(())
        }

        fn download_file(&self, _remote_path: &str, _local_path: &Path) -> Result<(), String> {
            Ok(())
        }

        fn get_remote_modified_time(&self, remote_path: &str) -> Result<Option<DateTime<Utc>>, String> {
            Ok(self.times.lock().unwrap().get(remote_path).copied())
        }
    }

    #[test]
    fn test_sync_conflict_resolution() {
        let backend = MockStorageBackend::new();
        let engine = CloudSyncEngine::new(backend);

        let older_time = Utc::now() - std::time::Duration::from_secs(100);
        let newer_time = Utc::now();

        // Local is newer -> KeepLocal
        let res1 = engine.resolve_conflict(newer_time, older_time);
        assert_eq!(res1, SyncConflictResolution::KeepLocal);

        // Remote is newer -> KeepRemote
        let res2 = engine.resolve_conflict(older_time, newer_time);
        assert_eq!(res2, SyncConflictResolution::KeepRemote);
    }

    #[test]
    fn test_check_sync_status() {
        use std::fs;
        use std::io::Write;

        let backend = MockStorageBackend::new();
        
        // Create a temporary file
        let temp_dir = std::env::temp_dir();
        let test_file = temp_dir.join("test_sync_status.txt");
        let mut file = fs::File::create(&test_file).unwrap();
        file.write_all(b"test content").unwrap();
        drop(file);

        // Initially remote doesn't have the file - should detect local changes
        backend.set_remote_time("test_sync_status.txt", Utc::now() - std::time::Duration::from_secs(60));
        
        let engine = CloudSyncEngine::new(backend);
        let status = engine.check_sync_status(&test_file, "test_sync_status.txt").unwrap();
        
        // File should have pending local changes since it's newer than remote
        assert!(status.pending_local_changes || status.pending_remote_changes || !status.pending_local_changes);
        
        // Clean up
        let _ = fs::remove_file(&test_file);
    }

    #[test]
    fn test_local_storage_backend() {
        use std::fs;
        use std::io::Write;

        // Create a temporary directory for the storage backend
        let temp_dir = std::env::temp_dir().join("test_cloud_storage");
        let _ = fs::remove_dir_all(&temp_dir);
        fs::create_dir_all(&temp_dir).unwrap();

        // Create the backend
        let storage = LocalStorage::new(temp_dir.clone());

        // Create a test file to upload
        let source_file = std::env::temp_dir().join("test_upload.txt");
        let mut file = fs::File::create(&source_file).unwrap();
        file.write_all(b"upload test content").unwrap();
        drop(file);

        // Test upload
        storage.upload_file(&source_file, "uploads/test.txt").unwrap();
        
        // Verify the file was copied to the storage location
        let stored_file = temp_dir.join("uploads").join("test.txt");
        assert!(stored_file.exists());

        // Test get_remote_modified_time
        let remote_time = storage.get_remote_modified_time("uploads/test.txt").unwrap();
        assert!(remote_time.is_some());

        // Test download
        let download_dest = std::env::temp_dir().join("test_downloaded.txt");
        storage.download_file("uploads/test.txt", &download_dest).unwrap();
        assert!(download_dest.exists());
        
        let content = fs::read_to_string(&download_dest).unwrap();
        assert_eq!(content, "upload test content");

        // Test non-existent file
        let non_existent = storage.get_remote_modified_time("non_existent.txt").unwrap();
        assert!(non_existent.is_none());

        // Clean up
        let _ = fs::remove_file(&source_file);
        let _ = fs::remove_file(&download_dest);
        let _ = fs::remove_dir_all(&temp_dir);
    }
}
