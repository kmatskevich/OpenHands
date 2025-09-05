import { useMutation, useQueryClient } from "@tanstack/react-query";
import OpenHands from "#/api/open-hands";

export const useUpdateConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: OpenHands.updateConfig,
    onSuccess: () => {
      // Invalidate and refetch config queries
      queryClient.invalidateQueries({ queryKey: ["full-config"] });
      queryClient.invalidateQueries({ queryKey: ["config"] });
    },
  });
};