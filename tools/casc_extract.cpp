#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <errno.h>
#include "CascLib.h"

static void mkdirs(const std::string& path) {
    std::string cur;
    for (size_t i = 0; i < path.size(); ++i) {
        char c = path[i];
        cur.push_back(c);
        if (c == '/' && cur.size() > 1) {
            mkdir(cur.c_str(), 0755);
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <d2r_install_dir> <output_dir> [mask]\n", argv[0]);
        fprintf(stderr, "Example: %s \"/home/grant/games/d2r/game/Diablo II Resurrected\" \"/tmp/extracted\" \"*excel*.txt\"\n", argv[0]);
        return 1;
    }

    const char* storagePath = argv[1];
    std::string outDir = argv[2];
    const char* mask = (argc >= 4) ? argv[3] : "*";

    HANDLE hStorage = NULL;
    if (!CascOpenStorage(storagePath, 0, &hStorage)) {
        fprintf(stderr, "Error: Failed to open CASC storage at '%s' (err=%u)\n", storagePath, GetCascError());
        return 2;
    }

    CASC_FIND_DATA findData;
    HANDLE hFind = CascFindFirstFile(hStorage, mask, &findData, NULL);
    if (hFind == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "No files found matching mask '%s' (err=%u)\n", mask, GetCascError());
        CascCloseStorage(hStorage);
        return 3;
    }

    int extracted = 0;
    do {
        if (!findData.bFileAvailable) continue;
        std::string relPath = findData.szFileName;
        // Strip leading "data:" or "data\\" prefix if present
        if (relPath.rfind("data:", 0) == 0) {
            relPath = relPath.substr(5);
        }
        for (char& c : relPath) {
            if (c == '\\') c = '/';
        }
        if (!relPath.empty() && relPath[0] == '/') {
            relPath = relPath.substr(1);
        }

        // Only extract files under data/global/excel/ if default mode, or everything matching mask
        HANDLE hFile = NULL;
        if (CascOpenFile(hStorage, findData.szFileName, 0, CASC_OPEN_BY_NAME, &hFile)) {
            std::string fullOut = outDir + "/" + relPath;
            mkdirs(fullOut);
            FILE* fp = fopen(fullOut.c_str(), "wb");
            if (fp) {
                char buf[65536];
                DWORD bytesRead = 0;
                while (CascReadFile(hFile, buf, sizeof(buf), &bytesRead) && bytesRead > 0) {
                    fwrite(buf, 1, bytesRead, fp);
                }
                fclose(fp);
                extracted++;
                printf("Extracted: %s\n", relPath.c_str());
            }
            CascCloseFile(hFile);
        }
    } while (CascFindNextFile(hFind, &findData));

    CascFindClose(hFind);
    CascCloseStorage(hStorage);
    printf("Done! Extracted %d files to %s\n", extracted, outDir.c_str());
    return 0;
}
