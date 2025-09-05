import { useQuery } from "@tanstack/react-query";
import OpenHands from "#/api/open-hands";

export const useDiagnostics = () =>
  useQuery({
    queryKey: ["diagnostics"],
    queryFn: () => OpenHands.getDiagnostics(),
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: false,
  });
