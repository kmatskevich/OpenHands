import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { FaInfoCircle, FaFolder, FaExclamationTriangle } from "react-icons/fa";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import { useUpdateConfig } from "#/hooks/mutation/use-update-config";
import { useValidateConfig } from "#/hooks/mutation/use-validate-config";
import { useDiagnostics } from "#/hooks/mutation/use-diagnostics";

interface LocalProjectSelectorProps {
  onProjectSelection: (projectPath: string | null) => void;
}

export function LocalProjectSelector({ onProjectSelection }: LocalProjectSelectorProps) {
  const { t } = useTranslation();
  const [selectedPath, setSelectedPath] = useState<string>("");
  const [manualPath, setManualPath] = useState<string>("");
  const [showManualInput, setShowManualInput] = useState(false);
  const [requiresRestart, setRequiresRestart] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  const updateConfigMutation = useUpdateConfig();
  const validateConfigMutation = useValidateConfig();
  const diagnosticsMutation = useDiagnostics();

  // Check if File System Access API is supported
  const isDirectoryPickerSupported = 'showDirectoryPicker' in window;

  // Load saved path from localStorage on mount
  useEffect(() => {
    const savedPath = localStorage.getItem('openhands-local-project-path');
    if (savedPath) {
      setSelectedPath(savedPath);
      setManualPath(savedPath);
      onProjectSelection(savedPath);
    }
  }, [onProjectSelection]);

  const handleDirectoryPicker = async () => {
    try {
      if ('showDirectoryPicker' in window) {
        // @ts-ignore - File System Access API
        const dirHandle = await window.showDirectoryPicker();
        const path = dirHandle.name; // This is simplified - in real implementation we'd need the full path
        setSelectedPath(path);
        setManualPath(path);
        localStorage.setItem('openhands-local-project-path', path);
        await updateProjectPath(path);
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('Directory picker error:', error);
      }
    }
  };

  const handleManualPathSubmit = async () => {
    if (manualPath.trim()) {
      const path = manualPath.trim();
      setSelectedPath(path);
      localStorage.setItem('openhands-local-project-path', path);
      await updateProjectPath(path);
    }
  };

  const updateProjectPath = async (path: string) => {
    try {
      const result = await updateConfigMutation.mutateAsync({
        runtime: {
          environment: 'local',
          local: {
            project_root: path
          }
        }
      });

      if (result.requires_restart) {
        setRequiresRestart(true);
      }

      onProjectSelection(path);

      // Validate the configuration
      await validatePath(path);
    } catch (error) {
      console.error('Failed to update config:', error);
    }
  };

  const validatePath = async (path: string) => {
    try {
      // First update the config, then validate
      await updateConfigMutation.mutateAsync({
        runtime: {
          environment: 'local',
          local: {
            project_root: path
          }
        }
      });

      // Then validate the current configuration
      const result = await validateConfigMutation.mutateAsync();

      setValidationErrors(result.errors || []);
      setValidationWarnings(result.warnings || []);
    } catch (error) {
      console.error('Validation failed:', error);
      setValidationErrors(['Failed to validate configuration']);
    }
  };

  const handleDiagnose = async () => {
    try {
      await diagnosticsMutation.mutateAsync();
      setShowDiagnostics(true);
    } catch (error) {
      console.error('Diagnostics failed:', error);
    }
  };

  const dismissRestartBanner = () => {
    setRequiresRestart(false);
  };

  return (
    <section
      data-testid="local-project-selector"
      className="w-full flex flex-col gap-6"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <h2 className="heading">{t("HOME$SELECT_PROJECT_FOLDER")}</h2>
        <TooltipButton
          testId="local-project-selector-info"
          tooltip={t("HOME$SELECT_PROJECT_FOLDER_TOOLTIP")}
          ariaLabel={t("HOME$SELECT_PROJECT_FOLDER_TOOLTIP")}
          className="text-[#9099AC] hover:text-white"
          placement="bottom"
          tooltipClassName="max-w-[348px]"
        >
          <FaInfoCircle size={16} />
        </TooltipButton>
      </div>

      {/* Restart Required Banner */}
      {requiresRestart && (
        <div className="bg-yellow-900/20 border border-yellow-600 rounded-lg p-4 flex items-start gap-3">
          <FaExclamationTriangle className="text-yellow-500 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-semibold text-yellow-200 mb-1">
              {t("HOME$RESTART_REQUIRED")}
            </h3>
            <p className="text-yellow-100 text-sm mb-2">
              {t("HOME$RESTART_REQUIRED_MESSAGE")}
            </p>
            <code className="bg-black/30 px-2 py-1 rounded text-xs">
              docker compose restart openhands
            </code>
          </div>
          <button
            onClick={dismissRestartBanner}
            className="text-yellow-400 hover:text-yellow-200 text-xl leading-none"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="bg-red-900/20 border border-red-600 rounded-lg p-4">
          <h3 className="font-semibold text-red-200 mb-2 flex items-center gap-2">
            <FaExclamationTriangle />
            {t("HOME$VALIDATION_ERRORS")}
          </h3>
          <ul className="text-red-100 text-sm space-y-1">
            {validationErrors.map((error, index) => (
              <li key={index}>• {error}</li>
            ))}
          </ul>
          {validationErrors.some(error => error.includes('mount')) && (
            <p className="text-red-100 text-sm mt-2">
              <a href="#" className="underline hover:no-underline">
                {t("HOME$MOUNTING_GUIDE_LINK")}
              </a>
            </p>
          )}
        </div>
      )}

      {/* Validation Warnings */}
      {validationWarnings.length > 0 && (
        <div className="bg-yellow-900/20 border border-yellow-600 rounded-lg p-4">
          <h3 className="font-semibold text-yellow-200 mb-2 flex items-center gap-2">
            <FaExclamationTriangle />
            {t("HOME$VALIDATION_WARNINGS")}
          </h3>
          <ul className="text-yellow-100 text-sm space-y-1">
            {validationWarnings.map((warning, index) => (
              <li key={index}>• {warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty State */}
      {!selectedPath && (
        <div className="text-center py-8 px-4 bg-gray-800/50 border-2 border-dashed border-gray-600 rounded-lg">
          <FaFolder className="mx-auto text-4xl text-gray-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-300 mb-2">
            {t("HOME$NO_FOLDER_SELECTED")}
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            {t("HOME$NO_FOLDER_SELECTED_DESCRIPTION")}
          </p>
        </div>
      )}

      {/* Folder Selection */}
      <div className="space-y-4">
        {/* Directory Picker Button */}
        {isDirectoryPickerSupported && (
          <button
            onClick={handleDirectoryPicker}
            disabled={updateConfigMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
          >
            <FaFolder />
            {t("HOME$CHOOSE_FOLDER")}
          </button>
        )}

        {/* Manual Path Input */}
        {(!isDirectoryPickerSupported || showManualInput) && (
          <div className="space-y-2">
            <label htmlFor="manual-path" className="block text-sm font-medium text-gray-300">
              {t("HOME$ENTER_ABSOLUTE_PATH")}
            </label>
            <div className="flex gap-2">
              <input
                id="manual-path"
                type="text"
                value={manualPath}
                onChange={(e) => setManualPath(e.target.value)}
                placeholder="/path/to/your/project"
                className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleManualPathSubmit}
                disabled={!manualPath.trim() || updateConfigMutation.isPending}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
              >
                {t("HOME$VALIDATE")}
              </button>
            </div>
          </div>
        )}

        {/* Toggle Manual Input */}
        {isDirectoryPickerSupported && !showManualInput && (
          <button
            onClick={() => setShowManualInput(true)}
            className="text-sm text-blue-400 hover:text-blue-300 underline"
          >
            Enter path manually
          </button>
        )}
      </div>

      {/* Selected Path Display */}
      {selectedPath && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">
            {t("HOME$SELECTED_PATH")}
          </label>
          <div className="px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-gray-300 font-mono text-sm">
            {selectedPath}
          </div>
        </div>
      )}

      {/* Helper Text */}
      <p className="text-sm text-gray-400">
        {t("HOME$LOCAL_RUNTIME_HELPER_TEXT")}
      </p>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleDiagnose}
          disabled={diagnosticsMutation.isPending}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white rounded-lg transition-colors"
        >
          {t("HOME$DIAGNOSE")}
        </button>

        {selectedPath && validationErrors.length === 0 && (
          <button
            onClick={() => onProjectSelection(selectedPath)}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors font-medium"
          >
            {t("HOME$LAUNCH")}
          </button>
        )}
      </div>

      {/* Diagnostics Modal/Display */}
      {showDiagnostics && diagnosticsMutation.data && (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-4 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-white">{t("HOME$DIAGNOSTICS")}</h3>
            <button
              onClick={() => setShowDiagnostics(false)}
              className="text-gray-400 hover:text-white"
            >
              ×
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <h4 className="font-medium text-gray-300 mb-1">{t("HOME$RUNTIME_INFO")}</h4>
              <pre className="text-xs bg-black/30 p-2 rounded overflow-x-auto">
                {JSON.stringify(diagnosticsMutation.data?.sections?.runtime || {}, null, 2)}
              </pre>
            </div>

            <div>
              <h4 className="font-medium text-gray-300 mb-1">{t("HOME$CONFIG_INFO")}</h4>
              <pre className="text-xs bg-black/30 p-2 rounded overflow-x-auto">
                {JSON.stringify(diagnosticsMutation.data?.sections?.configuration || {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
