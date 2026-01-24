// =============================================================================
// SERV.O v10.1 - MUTATION FACTORY
// =============================================================================
// Factory for creating React Query mutations with auto-invalidation
// =============================================================================

import { useMutation, useQueryClient } from '@tanstack/react-query';

/**
 * Creates a mutation hook with automatic query invalidation.
 *
 * @param {Object} config - Mutation configuration
 * @param {Function} config.mutationFn - The mutation function
 * @param {Function} config.getInvalidateKeys - Function that returns keys to invalidate (receives mutation variables)
 * @param {Function} [config.onSuccess] - Additional onSuccess callback
 * @param {Function} [config.onError] - Additional onError callback
 * @param {Object} [config.options] - Additional mutation options
 * @returns {Function} - React Query mutation hook
 *
 * @example
 * const useUpdateOrdine = createMutation({
 *   mutationFn: ({ id, data }) => ordiniApi.update(id, data),
 *   getInvalidateKeys: ({ id }) => [
 *     ordiniKeys.detail(id),
 *     ordiniKeys.lists(),
 *   ],
 * });
 */
export function createMutation({
  mutationFn,
  getInvalidateKeys,
  onSuccess: additionalOnSuccess,
  onError: additionalOnError,
  options = {},
}) {
  return function useMutationHook(hookOptions = {}) {
    const queryClient = useQueryClient();

    return useMutation({
      mutationFn,
      onSuccess: (data, variables, context) => {
        // Invalidate specified query keys
        if (getInvalidateKeys) {
          const keys = getInvalidateKeys(variables, data);
          if (Array.isArray(keys)) {
            keys.forEach(key => {
              if (key) {
                queryClient.invalidateQueries({ queryKey: key });
              }
            });
          }
        }

        // Call additional onSuccess handlers
        additionalOnSuccess?.(data, variables, context);
        hookOptions.onSuccess?.(data, variables, context);
      },
      onError: (error, variables, context) => {
        additionalOnError?.(error, variables, context);
        hookOptions.onError?.(error, variables, context);
      },
      ...options,
      ...hookOptions,
    });
  };
}

/**
 * Creates a simple mutation hook that invalidates a list of static keys.
 *
 * @param {Function} mutationFn - The mutation function
 * @param {Array} invalidateKeys - Static array of query keys to invalidate
 * @returns {Function} - React Query mutation hook
 *
 * @example
 * const useDeleteOrdine = createSimpleMutation(
 *   ordiniApi.delete,
 *   [ordiniKeys.lists()]
 * );
 */
export function createSimpleMutation(mutationFn, invalidateKeys = []) {
  return createMutation({
    mutationFn,
    getInvalidateKeys: () => invalidateKeys,
  });
}

/**
 * Creates a mutation that invalidates based on an ID from variables.
 *
 * @param {Function} mutationFn - The mutation function
 * @param {Function} getKeysFromId - Function that takes ID and returns keys
 * @param {string} [idField='id'] - The field name for ID in variables
 * @returns {Function} - React Query mutation hook
 *
 * @example
 * const useUpdateOrdine = createIdMutation(
 *   ordiniApi.update,
 *   (id) => [ordiniKeys.detail(id), ordiniKeys.lists()],
 *   'idTestata'
 * );
 */
export function createIdMutation(mutationFn, getKeysFromId, idField = 'id') {
  return createMutation({
    mutationFn,
    getInvalidateKeys: (variables) => {
      const id = typeof variables === 'object' ? variables[idField] : variables;
      return getKeysFromId(id);
    },
  });
}

export default createMutation;
