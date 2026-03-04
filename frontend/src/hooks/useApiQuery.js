import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import useApi from './useApi';

export function useApiQuery(queryKey, url, options = {}) {
  const api = useApi();
  return useQuery({
    queryKey,
    queryFn: async () => {
      const { data } = await api.get(url);
      return data;
    },
    ...options,
  });
}

export function useApiMutation(method, urlOrFn, options = {}) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body) => {
      const url = typeof urlOrFn === 'function' ? urlOrFn(body) : urlOrFn;
      if (method === 'delete') {
        const { data } = await api.delete(url);
        return data;
      }
      const { data } = await api[method](url, body);
      return data;
    },
    onSuccess: () => {
      if (options.invalidate) {
        options.invalidate.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
      }
    },
    ...options,
  });
}
