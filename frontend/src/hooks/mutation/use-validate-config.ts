import { useMutation } from "@tanstack/react-query";
import OpenHands from "#/api/open-hands";

export const useValidateConfig = () =>
  useMutation({
    mutationFn: () => OpenHands.validateConfig(),
  });