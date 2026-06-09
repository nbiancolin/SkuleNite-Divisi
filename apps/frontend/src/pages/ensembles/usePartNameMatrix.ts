import { useCallback, useEffect, useState } from "react";
import { apiService, type PartNameMatrix } from "../../services/apiService";

export function usePartNameMatrix(ensembleSlug: string) {
  const [matrix, setMatrix] = useState<PartNameMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!ensembleSlug) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getPartNameMatrix(ensembleSlug);
      setMatrix(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setMatrix(null);
    } finally {
      setLoading(false);
    }
  }, [ensembleSlug]);

  useEffect(() => {
    load();
  }, [load]);

  return { matrix, loading, error, reload: load };
}
