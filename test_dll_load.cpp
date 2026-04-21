#include <windows.h>
#include <stdio.h>

int main() {
    printf("Loading daw_engine.dll...\n");
    
    HMODULE hModule = LoadLibraryA("daw_engine.dll");
    if (!hModule) {
        DWORD error = GetLastError();
        printf("Failed to load DLL. Error: %lu\n", error);
        return 1;
    }
    
    printf("DLL loaded successfully at %p\n", hModule);
    
    // Try to get a function
    FARPROC proc = GetProcAddress(hModule, "opendaw_engine_init");
    if (proc) {
        printf("Found opendaw_engine_init at %p\n", proc);
    } else {
        printf("opendaw_engine_init not found\n");
    }
    
    proc = GetProcAddress(hModule, "daw_engine_init");
    if (proc) {
        printf("Found daw_engine_init at %p\n", proc);
    } else {
        printf("daw_engine_init not found\n");
    }
    
    FreeLibrary(hModule);
    printf("DLL unloaded successfully\n");
    
    return 0;
}
