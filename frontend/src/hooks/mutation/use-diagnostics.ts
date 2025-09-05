import { useMutation } from "@tanstack/react-query";
import OpenHands from "#/api/open-hands";

export const useDiagnostics = () =>
  useMutation({
    mutationFn: () => OpenHands.getDiagnostics(),
  });