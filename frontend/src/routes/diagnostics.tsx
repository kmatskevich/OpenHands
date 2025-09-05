import React from "react";
import { useTranslation } from "react-i18next";
import { useDiagnostics } from "#/hooks/query/use-diagnostics";
import { DiagnosticsResponse } from "#/api/open-hands.types";

interface StatusBadgeProps {
  status: "ok" | "warning" | "error";
  children: React.ReactNode;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, children }) => {
  const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium";
  const statusClasses = {
    ok: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
  };

  return (
    <span className={`${baseClasses} ${statusClasses[status]}`}>
      {children}
    </span>
  );
};

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, children }) => (
  <div className="bg-white shadow rounded-lg p-6 mb-6">
    <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
    {children}
  </div>
);

interface InfoRowProps {
  label: string;
  value: string | React.ReactNode;
  copyable?: boolean;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value, copyable = false }) => {
  const handleCopy = () => {
    if (typeof value === "string") {
      navigator.clipboard.writeText(value);
    }
  };

  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-200 last:border-b-0">
      <span className="text-sm font-medium text-gray-500">{label}</span>
      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-900">{value}</span>
        {copyable && typeof value === "string" && (
          <button
            onClick={handleCopy}
            className="text-blue-600 hover:text-blue-800 text-xs"
            title="Copy to clipboard"
          >
            Copy
          </button>
        )}
      </div>
    </div>
  );
};

const RestartBanner: React.FC<{ runtimeKind: string }> = ({ runtimeKind }) => {
  const getRestartCommand = () => {
    switch (runtimeKind) {
      case "docker":
        return "docker compose restart openhands";
      case "local":
        return "Stop the current process and run openhands again";
      default:
        return "Restart method depends on how OpenHands was started";
    }
  };

  const command = getRestartCommand();
  const isCommand = runtimeKind === "docker";

  const handleCopy = () => {
    if (isCommand) {
      navigator.clipboard.writeText(command);
    }
  };

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-6">
      <div className="flex">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-yellow-800">
            Restart Required
          </h3>
          <div className="mt-2 text-sm text-yellow-700">
            <p>Configuration changes require a restart to take effect.</p>
            <div className="mt-2 flex items-center space-x-2">
              {isCommand ? (
                <>
                  <code className="bg-yellow-100 px-2 py-1 rounded text-xs">
                    {command}
                  </code>
                  <button
                    onClick={handleCopy}
                    className="text-yellow-800 hover:text-yellow-900 text-xs underline"
                  >
                    Copy
                  </button>
                </>
              ) : (
                <span className="text-xs">{command}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export function DiagnosticsPage() {
  const { t } = useTranslation();
  const { data: diagnostics, isLoading, error } = useDiagnostics();

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Failed to load diagnostics
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>Unable to retrieve system diagnostics. Please try again later.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!diagnostics) {
    return null;
  }

  const hasErrors = diagnostics.validation.errors.length > 0;
  const hasWarnings = diagnostics.validation.warnings.length > 0;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Diagnostics</h1>
        <p className="mt-2 text-sm text-gray-600">
          Overview of your OpenHands system status and configuration
        </p>
      </div>

      {diagnostics.runtime.requires_restart && (
        <RestartBanner runtimeKind={diagnostics.runtime.kind} />
      )}

      {/* Runtime Section */}
      <Section title="Runtime">
        <div className="space-y-2">
          <InfoRow label="Runtime Type" value={diagnostics.runtime.kind} />
          <InfoRow
            label="Status"
            value={
              diagnostics.runtime.requires_restart ? (
                <StatusBadge status="warning">Restart Required</StatusBadge>
              ) : (
                <StatusBadge status="ok">Running</StatusBadge>
              )
            }
          />
        </div>
      </Section>

      {/* Paths Section */}
      <Section title="Paths">
        <div className="space-y-2">
          {diagnostics.paths.config_path && (
            <InfoRow
              label="Config File"
              value={diagnostics.paths.config_path}
              copyable
            />
          )}
          {diagnostics.paths.project_root && (
            <InfoRow
              label="Project Root"
              value={diagnostics.paths.project_root}
              copyable
            />
          )}
          {diagnostics.paths.workspace_base && (
            <InfoRow
              label="Workspace Base"
              value={diagnostics.paths.workspace_base}
              copyable
            />
          )}
          {diagnostics.paths.workspace_mount_path && (
            <InfoRow
              label="Workspace Mount"
              value={diagnostics.paths.workspace_mount_path}
              copyable
            />
          )}
        </div>
      </Section>

      {/* Memory Section */}
      <Section title="Project Memory">
        <div className="space-y-2">
          <InfoRow
            label="Status"
            value={
              diagnostics.memory.connected ? (
                <StatusBadge status="ok">Connected</StatusBadge>
              ) : (
                <StatusBadge status="warning">Not Available</StatusBadge>
              )
            }
          />
          {diagnostics.memory.backend && (
            <InfoRow label="Backend" value={diagnostics.memory.backend} />
          )}
          {diagnostics.memory.db_path && (
            <InfoRow
              label="Database Path"
              value={diagnostics.memory.db_path}
              copyable
            />
          )}
          <InfoRow label="Events Count" value={diagnostics.memory.events_count.toString()} />
          <InfoRow label="Files Indexed" value={diagnostics.memory.files_indexed.toString()} />
          {diagnostics.memory.last_event_ts && (
            <InfoRow label="Last Event" value={diagnostics.memory.last_event_ts} />
          )}
        </div>
        {!diagnostics.memory.connected && (
          <div className="mt-4 text-sm text-gray-600">
            <p>Project memory is only available in local runtime mode.</p>
            <a
              href="/docs/project-memory"
              className="text-blue-600 hover:text-blue-800 underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Learn more about Project Memory
            </a>
          </div>
        )}
      </Section>

      {/* Validation Section */}
      <Section title="Validation">
        <div className="space-y-4">
          <InfoRow
            label="Status"
            value={
              hasErrors ? (
                <StatusBadge status="error">Errors Found</StatusBadge>
              ) : hasWarnings ? (
                <StatusBadge status="warning">Warnings</StatusBadge>
              ) : (
                <StatusBadge status="ok">All Good</StatusBadge>
              )
            }
          />

          {diagnostics.validation.errors.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-red-800 mb-2">Errors:</h4>
              <ul className="space-y-1">
                {diagnostics.validation.errors.map((error, index) => (
                  <li key={index} className="text-sm text-red-700 flex items-start">
                    <span className="text-red-500 mr-2">•</span>
                    {error}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {diagnostics.validation.warnings.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-yellow-800 mb-2">Warnings:</h4>
              <ul className="space-y-1">
                {diagnostics.validation.warnings.map((warning, index) => (
                  <li key={index} className="text-sm text-yellow-700 flex items-start">
                    <span className="text-yellow-500 mr-2">•</span>
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Section>

      {/* Environment Section */}
      <Section title="Environment">
        <div className="space-y-2">
          <InfoRow
            label="Status"
            value={
              diagnostics.env.openhands_overrides.length > 0 ? (
                <StatusBadge status="warning">Overrides Detected</StatusBadge>
              ) : (
                <StatusBadge status="ok">Default Configuration</StatusBadge>
              )
            }
          />

          {diagnostics.env.openhands_overrides.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Environment Overrides:</h4>
              <ul className="space-y-1">
                {diagnostics.env.openhands_overrides.map((override, index) => (
                  <li key={index} className="text-sm text-gray-600 flex items-center">
                    <code className="bg-gray-100 px-2 py-1 rounded text-xs mr-2">
                      {override}
                    </code>
                    <span className="text-gray-500">(value masked)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Section>

      {/* Versions Section */}
      <Section title="Versions">
        <div className="space-y-2">
          {diagnostics.versions.app_version && (
            <InfoRow label="App Version" value={diagnostics.versions.app_version} />
          )}
          {diagnostics.versions.git_sha && (
            <InfoRow label="Git SHA" value={diagnostics.versions.git_sha} />
          )}
          {diagnostics.versions.git_branch && (
            <InfoRow label="Git Branch" value={diagnostics.versions.git_branch} />
          )}
        </div>
      </Section>
    </div>
  );
}
