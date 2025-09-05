import { useState } from "react";

export interface FolderPickerResult {
  path: string | null;
  error: string | null;
}

export function useFolderPicker() {
  const [isPickerSupported] = useState(() => 'showDirectoryPicker' in window);

  const pickFolder = async (): Promise<FolderPickerResult> => {
    if (!isPickerSupported) {
      return {
        path: null,
        error: "Directory picker not supported in this browser"
      };
    }

    try {
      // @ts-ignore - File System Access API
      const dirHandle = await window.showDirectoryPicker();
      // Note: In a real implementation, we'd need to get the full path
      // For now, we'll use the directory name as a placeholder
      return {
        path: dirHandle.name,
        error: null
      };
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        return {
          path: null,
          error: null // User cancelled, not an error
        };
      }
      return {
        path: null,
        error: (error as Error).message
      };
    }
  };

  return {
    pickFolder,
    isPickerSupported
  };
}
