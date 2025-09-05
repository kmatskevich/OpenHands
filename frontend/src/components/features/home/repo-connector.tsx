import { useTranslation } from "react-i18next";
import { FaInfoCircle } from "react-icons/fa";
import { ConnectToProviderMessage } from "./connect-to-provider-message";
import { RepositorySelectionForm } from "./repo-selection-form";
import { LocalProjectSelector } from "./local-project-selector";
import { useConfig } from "#/hooks/query/use-config";
import { useFullConfig } from "#/hooks/query/use-full-config";
import { RepoProviderLinks } from "./repo-provider-links";
import { useUserProviders } from "#/hooks/use-user-providers";
import { GitRepository } from "#/types/git";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";

interface RepoConnectorProps {
  onRepoSelection: (repo: GitRepository | null) => void;
}

export function RepoConnector({ onRepoSelection }: RepoConnectorProps) {
  const { providers } = useUserProviders();
  const { data: config } = useConfig();
  const { data: fullConfig, isLoading: isLoadingFullConfig } = useFullConfig();
  const { t } = useTranslation();

  const isSaaS = config?.APP_MODE === "saas";
  const providersAreSet = providers.length > 0;
  
  // Determine runtime environment
  const runtimeEnvironment = fullConfig?.runtime?.environment || 'docker';
  const isLocalRuntime = runtimeEnvironment === 'local';

  // Show loading state while fetching config
  if (isLoadingFullConfig) {
    return (
      <section
        data-testid="repo-connector"
        className="w-full flex flex-col gap-6"
      >
        <div className="flex items-center gap-2">
          <h2 className="heading">{t("HOME$LOADING")}</h2>
        </div>
        <div className="animate-pulse bg-gray-700 h-20 rounded-lg"></div>
      </section>
    );
  }

  // For local runtime, show the local project selector
  if (isLocalRuntime) {
    return (
      <LocalProjectSelector 
        onProjectSelection={(projectPath) => {
          // Convert project path to a pseudo GitRepository for compatibility
          if (projectPath) {
            onRepoSelection({
              id: `local-${Date.now()}`,
              full_name: projectPath,
              git_provider: 'local' as any, // Local projects don't have a git provider
              is_public: false,
              name: projectPath.split('/').pop() || 'local-project',
              html_url: `file://${projectPath}`,
              clone_url: `file://${projectPath}`,
              default_branch: 'main',
            } as GitRepository);
          } else {
            onRepoSelection(null);
          }
        }}
      />
    );
  }

  // For docker runtime, show the existing repository connector
  return (
    <section
      data-testid="repo-connector"
      className="w-full flex flex-col gap-6"
    >
      <div className="flex items-center gap-2">
        <h2 className="heading">{t("HOME$CONNECT_TO_REPOSITORY")}</h2>
        <TooltipButton
          testId="repo-connector-info"
          tooltip={t("HOME$CONNECT_TO_REPOSITORY_TOOLTIP")}
          ariaLabel={t("HOME$CONNECT_TO_REPOSITORY_TOOLTIP")}
          className="text-[#9099AC] hover:text-white"
          placement="bottom"
          tooltipClassName="max-w-[348px]"
        >
          <FaInfoCircle size={16} />
        </TooltipButton>
      </div>

      {!providersAreSet && <ConnectToProviderMessage />}
      {providersAreSet && (
        <RepositorySelectionForm onRepoSelection={onRepoSelection} />
      )}

      {isSaaS && providersAreSet && <RepoProviderLinks />}
    </section>
  );
}
