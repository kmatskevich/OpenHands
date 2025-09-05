import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { BrandButton } from "./brand-button";

interface RestartBannerProps {
  runtime: "docker" | "local";
  onDismiss?: () => void;
}

export function RestartBanner({ runtime, onDismiss }: RestartBannerProps) {
  const { t } = useTranslation();

  const getRestartCommand = () => {
    if (runtime === "docker") {
      return "docker compose restart openhands";
    }
    return "# Stop the current process and restart with: make run";
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(getRestartCommand());
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = getRestartCommand();
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
    }
  };

  return (
    <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4 mb-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-yellow-200 mb-2">
            {t(I18nKey.SETTINGS$RESTART_REQUIRED)}
          </h3>
          <p className="text-xs text-yellow-300 mb-3">
            {t(I18nKey.SETTINGS$RESTART_COMMAND)}
          </p>
          <div className="bg-black/30 rounded p-2 font-mono text-xs text-yellow-100 mb-3">
            {getRestartCommand()}
          </div>
          <BrandButton
            type="button"
            variant="secondary"
            onClick={copyToClipboard}
          >
            Copy Command
          </BrandButton>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-yellow-400 hover:text-yellow-200 ml-4"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}
