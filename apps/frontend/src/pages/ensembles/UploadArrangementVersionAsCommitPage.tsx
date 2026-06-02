import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Alert,
  Container,
  FileInput,
  Button,
  Title,
  Center,
  Text,
  Notification,
  TextInput,
  Checkbox,
  Stack,
  Paper,
  Loader,
} from "@mantine/core";
import { X, UploadCloud } from "lucide-react";
import { apiService } from "../../services/apiService";
import type { Arrangement, Commit } from "../../services/apiService";
import { CreateCommitError } from "../../services/apiService";
import { formatArrangementTitle } from "../../context/pageTitleUtils";
import { usePageTitle } from "../../context/usePageTitle";

type UploadErrorKind = "generic" | "complicated_merge" | "merge_conflict_tip";

export default function UploadArrangementVersionFromCommitPage() {
  const { arrangementId = "0" } = useParams();
  const [arrangement, setArrangement] = useState<Arrangement | undefined>(undefined);
  usePageTitle(
    arrangement ? `${formatArrangementTitle(arrangement)} - Upload Commit` : null,
  );
  const [latestCommit, setLatestCommit] = useState<Commit | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [commitMessage, setCommitMessage] = useState<string>("");
  const [noConflicts, setNoConflicts] = useState<boolean>(true);
  const [forceUpload, setForceUpload] = useState(false);

  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<UploadErrorKind>("generic");

  const numericArrangementId = Number(arrangementId);
  const latestCommitHasMergeConflict = latestCommit?.is_merge_conflict ?? false;
  const latestCommitDownloadUrl = latestCommit
    ? apiService.getCommitMsczDownloadUrl(numericArrangementId, latestCommit.id)
    : null;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [arrangementData, noConflictsData, commits] = await Promise.all([
          apiService.getArrangementById(numericArrangementId),
          apiService.checkScoreVersion(numericArrangementId),
          apiService.getArrangementCommits(numericArrangementId),
        ]);
        setArrangement(arrangementData);
        setNoConflicts(noConflictsData);
        setLatestCommit(commits[0] ?? null);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
          setErrorKind("generic");
        }
      }
    };

    if (arrangementId) {
      fetchData();
    }
  }, [arrangementId, numericArrangementId]);

  const clearError = () => {
    setError(null);
    setErrorKind("generic");
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    clearError();
    try {
      await apiService.createArrangementCommit(
        numericArrangementId,
        file,
        commitMessage,
        forceUpload
      );
      navigate(`/app/arrangements/${arrangementId}`);
    } catch (err: unknown) {
      console.error("Upload error:", err);
      if (err instanceof CreateCommitError) {
        if (err.kind === "merge_error") {
          setErrorKind("complicated_merge");
          setError(
            err.mergeError ||
              "Unable to merge scores automatically. Enable “Force upload” to replace the latest commit with your file."
          );
          setForceUpload(true);
          return;
        }
        if (err.kind === "client_error") {
          setErrorKind("merge_conflict_tip");
          setError(err.clientError || err.message);
          return;
        }
      }
      setErrorKind("generic");
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        {arrangement?.title}
      </Title>
      <Center>
        <Text>
          Upload score as a new commit, then create a version from that commit.
        </Text>
      </Center>

      {latestCommitHasMergeConflict && (
        <Container size="md" mb="lg" mt="xs">
          <Alert color="red" title="Unresolved merge conflict" mb="sm">
            The latest commit has a merge conflict. Download the merged score, fix it in
            MuseScore, then upload your corrected file with{" "}
            <strong>Force upload</strong> enabled below.
            {latestCommitDownloadUrl && (
              <>
                {" "}
                <Button
                  component="a"
                  href={latestCommitDownloadUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="white"
                  color="red"
                  size="compact-sm"
                  mt="xs"
                >
                  Download conflict score
                </Button>
              </>
            )}
          </Alert>
        </Container>
      )}

      {!noConflicts && (
        <Container size="md" mb="lg" mt="xs">
          <Alert color="yellow" title="Warning" mb="sm">
            This arrangement has been updated since you last downloaded. 
            Divisi App will try and perform an automated merge, but a merge conflict may arise.
          </Alert>
        </Container>
      )}

      {isUploading && (
        <Paper withBorder p="md" mt="md" mb="md">
          <Stack align="center" gap="sm">
            <Loader size="md" />
            <Text fw={600}>Processing…</Text>
            <Text size="sm" c="dimmed" ta="center">
              Merging your score may take a minute. Do not leave this page until the upload
              finishes.
            </Text>
          </Stack>
        </Paper>
      )}

      <FileInput
        placeholder="Choose a file"
        label="Select file"
        leftSection={<UploadCloud size={18} />}
        value={file}
        onChange={setFile}
        accept="*/*"
        mb="md"
        disabled={isUploading}
      />
      <TextInput
        label="Commit message (optional)"
        value={commitMessage}
        onChange={(e) => setCommitMessage(e.currentTarget.value)}
        placeholder="Describe this change"
        mt="md"
        disabled={isUploading}
      />

      <Checkbox
        mt="md"
        label="Force upload (skip merge; replace latest commit)"
        description="Use after fixing a merge conflict, or when automatic merge fails."
        checked={forceUpload}
        onChange={(e) => setForceUpload(e.currentTarget.checked)}
        disabled={isUploading}
      />

      <Button
        mt="md"
        onClick={handleUpload}
        disabled={!file || isUploading}
        fullWidth
        loading={isUploading}
      >
        Upload New Commit
      </Button>

      {error && errorKind === "complicated_merge" && (
        <Alert
          color="orange"
          title="Automatic merge failed"
          mt="xl"
          withCloseButton
          onClose={clearError}
        >
          {error} Check <strong>Force upload</strong> above and try again.
        </Alert>
      )}

      {error && errorKind === "merge_conflict_tip" && (
        <Alert color="red" title="Merge conflict" mt="xl" withCloseButton onClose={clearError}>
          {error}
          {latestCommitDownloadUrl ? (
            <Button
              component="a"
              href={latestCommitDownloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              variant="white"
              color="red"
              size="compact-sm"
              mt="sm"
            >
              Download latest commit to fix
            </Button>
          ) : (
            <Text size="sm" mt="xs">
              <Link to={`/app/arrangements/${arrangementId}`}>
                Go to the arrangement page
              </Link>{" "}
              to download the latest commit, fix the merge in MuseScore, then return here
              with force upload enabled.
            </Text>
          )}
        </Alert>
      )}

      {error && errorKind === "generic" && (
        <Notification
          mt="xl"
          icon={<X size={18} />}
          color="red"
          title="Error"
          onClose={clearError}
        >
          {error}
        </Notification>
      )}
    </Container>
  );
}
