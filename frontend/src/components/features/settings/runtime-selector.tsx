import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface RuntimeSelectorProps {
  value: "docker" | "local";
  onChange: (value: "docker" | "local") => void;
  disabled?: boolean;
}

export function RuntimeSelector({ value, onChange, disabled }: RuntimeSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-[#F9FBFE]">
        {t(I18nKey.SETTINGS$RUNTIME)}
      </label>
      <p className="text-xs text-[#A3A3A3] mb-2">
        {t(I18nKey.SETTINGS$RUNTIME_DESCRIPTION)}
      </p>
      <div className="flex gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="runtime"
            value="docker"
            checked={value === "docker"}
            onChange={(e) => onChange(e.target.value as "docker" | "local")}
            disabled={disabled}
            className="w-4 h-4 text-primary bg-transparent border-2 border-[#525252] focus:ring-primary focus:ring-2"
          />
          <span className="text-sm text-[#F9FBFE]">
            {t(I18nKey.SETTINGS$RUNTIME_DOCKER)}
          </span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="runtime"
            value="local"
            checked={value === "local"}
            onChange={(e) => onChange(e.target.value as "docker" | "local")}
            disabled={disabled}
            className="w-4 h-4 text-primary bg-transparent border-2 border-[#525252] focus:ring-primary focus:ring-2"
          />
          <span className="text-sm text-[#F9FBFE]">
            {t(I18nKey.SETTINGS$RUNTIME_LOCAL)}
          </span>
        </label>
      </div>
    </div>
  );
}
