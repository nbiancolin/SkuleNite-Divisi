import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService } from "../../services/apiService";
import type { Arrangement, Commit, EditableArrangementData, VersionHistoryItem } from "../../services/apiService";
import type { PreviewStyleName } from "../../components/ScoreTitlePreview";

export function useArrangementDetailPage() {
  const { arrangementId: arrangementIdParam = "1" } = useParams();
  const arrangementId = arrangementIdParam;
  const [arrangement, setArrangement] = useState<Arrangement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mvtNo, setMvtNo] = useState<string>("");

  const [selectedStyle, setSelectedStyle] = useState<PreviewStyleName>("broadway");

  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<EditableArrangementData>({
    ensemble: 0,
    title: "",
    subtitle: "",
    style: "broadway",
    composer: "",
    mvt_no: "",
  });
  const [saveLoading, setSaveLoading] = useState(false);

  const [msczUrl, setMsczUrl] = useState<string>("");
  const [rawMsczUrl, setRawMsczUrl] = useState<string>("");
  const [scoreUrl, setScoreUrl] = useState<string>("");
  const [allPartsUrl, setAllPartsUrl] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [audioActionLoading, setAudioActionLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState<boolean>(true);
  const [exportError, setExportError] = useState<boolean>(false);

  const [versionHistory, setVersionHistory] = useState<VersionHistoryItem[]>([]);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [versionHistoryLoading, setVersionHistoryLoading] = useState(false);
  const [selectedVersionForDownload, setSelectedVersionForDownload] = useState<number | null>(null);
  const [versionDownloadModal, setVersionDownloadModal] = useState(false);
  const [versionDownloadLoading, setVersionDownloadLoading] = useState(false);
  const [versionDownloadLinks, setVersionDownloadLinks] = useState({
    rawMsczUrl: "",
    msczUrl: "",
    scoreUrl: "",
    exportLoading: false,
    exportError: false,
  });
  const [parts, setParts] = useState<
    Array<{
      id: number;
      name: string;
      is_score: boolean;
      file_url: string;
      download_url: string;
    }>
  >([]);
  const [partsLoading, setPartsLoading] = useState(false);

  const [latestVersionParts, setLatestVersionParts] = useState<
    Array<{
      id: number;
      name: string;
      is_score: boolean;
      file_url: string;
      download_url: string;
    }>
  >([]);
  const [latestVersionPartsLoading, setLatestVersionPartsLoading] = useState(false);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [commitsLoading, setCommitsLoading] = useState(false);
  const [showCommitHistory, setShowCommitHistory] = useState(false);

  const audioState = arrangement?.latest_version?.audio_state ?? "none";

  const navigate = useNavigate();

  const pollAudioState = async (aid: number) => {
    let done = false;

    while (!done) {
      await new Promise((r) => setTimeout(r, 1500));

      const data = await apiService.getArrangementById(aid);

      const state = data.latest_version?.audio_state;

      if (state === "complete" || state === "error") {
        setArrangement(data);
        done = true;
      }
    }
  };

  const handleAudioButtonClick = async () => {
    if (!arrangement?.latest_version) return;

    const { id, audio_state } = arrangement.latest_version;

    if (audio_state === "none") {
      setAudioActionLoading(true);
      await apiService.triggerAudioExport(id);
      await pollAudioState(arrangement.id);
      setAudioActionLoading(false);
      return;
    }

    if (audio_state === "complete") {
      window.open(audioUrl, "_blank");
      return;
    }

    if (audio_state === "error") {
      alert("There was an error exporting audio. Tell Nick!");
    }
  };

  const getDownloadLinks = async (arrangementVersionId: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDownloadLinksForVersion(arrangementVersionId);
      setRawMsczUrl(data.raw_mscz_url);
      setMsczUrl(data.processed_mscz_url);
      setScoreUrl(data.score_parts_pdf_link);
      setAllPartsUrl(data.combined_parts_pdf_url || data.download_all_parts_url || "");
      setAudioUrl(data.mp3_link);
      setExportLoading(data.is_processing);
      setExportError(data.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch version download links");
    } finally {
      setLoading(false);
    }
  };

  const fetchVersionHistory = async (aid: number) => {
    try {
      setVersionHistoryLoading(true);
      const history = await apiService.getVersionHistory(aid);
      setVersionHistory(history);
    } catch (err) {
      console.error("Failed to fetch version history:", err);
    } finally {
      setVersionHistoryLoading(false);
    }
  };

  const fetchLatestVersionParts = async (versionId: number) => {
    try {
      setLatestVersionPartsLoading(true);
      const partsData = await apiService.getPartsForVersion(versionId);
      setLatestVersionParts(partsData.parts || []);
    } catch (err) {
      console.error("Failed to fetch latest version parts:", err);
      setLatestVersionParts([]);
    } finally {
      setLatestVersionPartsLoading(false);
    }
  };

  const fetchCommits = async (aid: number) => {
    try {
      setCommitsLoading(true);
      const commitData = await apiService.getArrangementCommits(aid);
      setCommits(commitData);
    } catch (err) {
      console.error("Failed to fetch commit history:", err);
    } finally {
      setCommitsLoading(false);
    }
  };

  const handleVersionDownload = async (versionId: number) => {
    setSelectedVersionForDownload(versionId);
    setVersionDownloadModal(true);
    setVersionDownloadLoading(true);
    setPartsLoading(true);

    try {
      const data = await apiService.getDownloadLinksForVersion(versionId);
      setVersionDownloadLinks({
        rawMsczUrl: data.raw_mscz_url,
        msczUrl: data.processed_mscz_url,
        scoreUrl: data.score_parts_pdf_link || data.score_pdf_url,
        exportLoading: data.is_processing,
        exportError: data.error,
      });

      try {
        const partsData = await apiService.getPartsForVersion(versionId);
        setParts(partsData.parts || []);
      } catch (err) {
        console.error("Failed to fetch parts:", err);
        if (data.parts && data.parts.length > 0) {
          setParts(data.parts);
        } else {
          setParts([]);
        }
      }
    } catch {
      setVersionDownloadLinks((prev) => ({ ...prev, exportError: true }));
    } finally {
      setVersionDownloadLoading(false);
      setPartsLoading(false);
    }
  };

  const fetchArrangement = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getArrangementById(id);
      setArrangement(data);
      setMvtNo(data.mvt_no);

      setEditData({
        ensemble: data.ensemble || 0,
        title: data.title || "",
        subtitle: data.subtitle || "",
        style: data.style,
        composer: data.composer || "",
        mvt_no: data.mvt_no || "",
      });

      if (data?.latest_version?.id) {
        await getDownloadLinks(data.latest_version.id);
        await fetchLatestVersionParts(data.latest_version.id);
      } else {
        setExportLoading(false);
        setExportError(false);
        setRawMsczUrl("");
        setMsczUrl("");
        setScoreUrl("");
        setAudioUrl("");
      }

      await fetchVersionHistory(id);
      await fetchCommits(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch arrangement");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveChanges = async () => {
    if (!arrangement) return;

    try {
      setSaveLoading(true);
      editData.style = selectedStyle;
      editData.mvt_no = mvtNo;
      await apiService.updateArrangement(arrangement.id, editData);

      await fetchArrangement(+arrangementId);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaveLoading(false);
    }
  };

  const handleCancelEdit = () => {
    if (arrangement) {
      setEditData({
        ensemble: arrangement.ensemble || 0,
        title: arrangement.title || "",
        subtitle: arrangement.subtitle || "",
        style: arrangement.style,
        composer: arrangement.composer || "",
        mvt_no: arrangement.mvt_no || "",
      });
    }
    setIsEditing(false);
  };

  useEffect(() => {
    fetchArrangement(+arrangementId);
  }, [arrangementId]);

  const handleRefresh = () => {
    fetchArrangement(+arrangementId);
  };

  const handleBackClick = () => {
    navigate(`/app/ensembles/${arrangement?.ensemble_slug}/arrangements`);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const latestCommitMsczDownloadUrl = arrangement
    ? apiService.getLatestCommitMsczDownloadUrl(arrangement.id)
    : "";
  const canDownloadLatestCommitMscz = commits.length > 0;

  return {
    arrangementId,
    arrangement,
    loading,
    error,
    mvtNo,
    setMvtNo,
    selectedStyle,
    setSelectedStyle,
    isEditing,
    setIsEditing,
    editData,
    setEditData,
    saveLoading,
    msczUrl,
    rawMsczUrl,
    scoreUrl,
    allPartsUrl,
    audioUrl,
    audioActionLoading,
    exportLoading,
    exportError,
    versionHistory,
    showVersionHistory,
    setShowVersionHistory,
    versionHistoryLoading,
    selectedVersionForDownload,
    setSelectedVersionForDownload,
    versionDownloadModal,
    setVersionDownloadModal,
    versionDownloadLoading,
    versionDownloadLinks,
    parts,
    partsLoading,
    latestVersionParts,
    latestVersionPartsLoading,
    commits,
    commitsLoading,
    showCommitHistory,
    setShowCommitHistory,
    audioState,
    handleAudioButtonClick,
    handleVersionDownload,
    handleSaveChanges,
    handleCancelEdit,
    handleRefresh,
    handleBackClick,
    formatTimestamp,
    latestCommitMsczDownloadUrl,
    canDownloadLatestCommitMscz,
  };
}
