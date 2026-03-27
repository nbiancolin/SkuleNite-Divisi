import { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  SegmentedControl,
  Collapse,
  TextInput,
  Stack,
  Group,
  Paper,
  Center,
  Loader,
} from "@mantine/core";
import { X } from "lucide-react";
import { apiService } from "../../services/apiService";
import type { Arrangement, ArrangementCommitListItem } from "../../services/apiService";

export default function CreateVersionFromCommitPage() {
  const { arrangementId = "0", commitId = "" } = useParams();
  const navigate = useNavigate();

  const [arrangement, setArrangement] = useState<Arrangement | undefined>(undefined);
  const [commits, setCommits] = useState<ArrangementCommitListItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pageLoading, setPageLoading] = useState(true);

  const [versionType, setVersionType] = useState<string>("patch");
  const [measuresPerLineScore, setMeasuresPerLineScore] = useState<string>("8");
  const [measuresPerLinePart, setMeasuresPerLinePart] = useState<string>("6");
  const [linesPerPage, setLinesPerPage] = useState<string>("8");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const effectiveCommitId = useMemo(() => {
    const t = (commitId ?? "").trim();
    if (!t) return null;
    const n = Number(t);
    return Number.isInteger(n) ? n : null;
  }, [commitId]);

  const commit = useMemo(() => {
    if (effectiveCommitId == null) return undefined;
    return commits.find((c) => c.id === effectiveCommitId);
  }, [commits, effectiveCommitId]);

  useEffect(() => {
    const fetchData = async () => {
      if (!arrangementId || !commitId) {
        setLoadError("Missing arrangement or commit in the URL.");
        setPageLoading(false);
        return;
      }
      setLoadError(null);
      setPageLoading(true);
      try {
        const [arrangementData, commitData] = await Promise.all([
          apiService.getArrangementById(+arrangementId),
          apiService.getArrangementCommits(+arrangementId),
        ]);
        setArrangement(arrangementData);
        setCommits(commitData);
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : "Failed to load arrangement");
      } finally {
        setPageLoading(false);
      }
    };
    fetchData();
  }, [arrangementId, commitId]);

  const getNewVersionNumber = (type?: string): string => {
    if (!arrangement?.latest_version_num) return "1.0.0";

    const currentVersion = arrangement.latest_version_num;
    const versionParts = currentVersion.split(".").map((part) => parseInt(part, 10));

    while (versionParts.length < 3) {
      versionParts.push(0);
    }

    let [major, minor, patch] = versionParts;

    if (isNaN(major)) {
      major = 0;
    }

    const targetType = type || versionType;

    switch (targetType) {
      case "major":
        major = major + 1;
        minor = 0;
        patch = 0;
        break;
      case "minor":
        minor += 1;
        patch = 0;
        break;
      case "patch":
        patch += 1;
        break;
      default:
        break;
    }

    return `${major}.${minor}.${patch}`;
  };

  const handleCreate = async () => {
    if (effectiveCommitId == null) {
      setSubmitError(
        "Could not resolve this commit. Open this screen from the arrangement's commit list, or use the commit id in the URL."
      );
      return;
    }

    const nScore = parseInt(measuresPerLineScore, 10);
    const nPart = parseInt(measuresPerLinePart, 10);
    const nLines = parseInt(linesPerPage, 10);
    if ([nScore, nPart, nLines].some((n) => isNaN(n) || n < 1)) {
      setSubmitError("Measures per line and lines per page must be positive numbers.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await apiService.createArrangementVersionFromCommit(effectiveCommitId, {
        version_type: versionType,
        num_measures_per_line_score: nScore,
        num_measures_per_line_part: nPart,
        num_lines_per_page: nLines,
      });
      navigate(`/app/arrangements/${arrangementId}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create version from commit");
    } finally {
      setIsSubmitting(false);
    }
  };

  const arrangementPath = `/app/arrangements/${arrangementId}`;

  if (loadError) {
    return (
      <Container size="sm" py="xl">
        <Notification color="red" title="Error" icon={<X size={18} />}>
          {loadError}
        </Notification>
        <Button component={Link} to={arrangementPath} mt="md" variant="light">
          Back to arrangement
        </Button>
      </Container>
    );
  }

  if (pageLoading) {
    return (
      <Container size="sm" py="xl">
        <Center py="xl">
          <Loader />
        </Center>
      </Container>
    );
  }

  const missingCommitDetails = !commit && commits.length > 0 && effectiveCommitId != null;

  return (
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <div>
          <Button component={Link} to={arrangementPath} variant="subtle" size="compact-sm" mb="xs">
            ← Back to arrangement
          </Button>
          <Title order={2}>{arrangement?.title ?? "…"}</Title>
          <Text c="dimmed" size="sm" mt="xs">
            Create a scored version from an existing commit
          </Text>
        </div>

        <Paper withBorder p="md" radius="md">
          <Text size="sm" fw={600} mb={4}>
            Commit
          </Text>
          <Text ff="monospace" size="sm">
            {commitId || "(missing)"}
          </Text>
          {commit && (
            <>
              <Text size="sm" mt="sm">
                {commit.message || "(no message)"}
              </Text>
              <Text c="dimmed" size="xs" mt={4}>
                {new Date(commit.timestamp).toLocaleString()}
              </Text>
            </>
          )}
          {missingCommitDetails && (
            <Text c="orange" size="sm" mt="sm">
              This commit id does not match the loaded history. Use the button on the arrangement page
              so the correct commit is selected, or put the correct commit id in the URL.
            </Text>
          )}
        </Paper>

        <div>
          <Text size="sm" fw={500} mb="xs">
            Version bump
          </Text>
          <SegmentedControl
            fullWidth
            size="md"
            value={versionType}
            onChange={setVersionType}
            data={[
              { label: `Major (${getNewVersionNumber("major")})`, value: "major" },
              { label: `Minor (${getNewVersionNumber("minor")})`, value: "minor" },
              { label: `Patch (${getNewVersionNumber("patch")})`, value: "patch" },
            ]}
          />
        </div>

        <Center>
          <Text
            onClick={() => setShowAdvanced((o) => !o)}
            style={{ cursor: "pointer", textDecoration: "underline" }}
            c="blue"
            size="sm"
          >
            {showAdvanced ? "Hide advanced layout options" : "Advanced layout options"}
          </Text>
        </Center>

        <Collapse in={showAdvanced}>
          <Text size="sm" mb="sm">
            Defaults work for most charts. Adjust if your meter or page breaks need different density.
          </Text>
          <TextInput
            label="Measures per line (score)"
            value={measuresPerLineScore}
            onChange={(e) => setMeasuresPerLineScore(e.currentTarget.value)}
            type="number"
            min={1}
          />
          <TextInput
            label="Measures per line (part)"
            value={measuresPerLinePart}
            onChange={(e) => setMeasuresPerLinePart(e.currentTarget.value)}
            type="number"
            min={1}
            mt="md"
          />
          <TextInput
            label="Lines per page (part)"
            value={linesPerPage}
            onChange={(e) => setLinesPerPage(e.currentTarget.value)}
            type="number"
            min={1}
            mt="md"
          />
        </Collapse>

        <Group>
          <Button onClick={handleCreate} loading={isSubmitting} disabled={effectiveCommitId == null}>
            Create version {getNewVersionNumber()}
          </Button>
          <Button component={Link} to={arrangementPath} variant="default">
            Cancel
          </Button>
        </Group>

        {submitError && (
          <Notification
            icon={<X size={18} />}
            color="red"
            title="Error"
            onClose={() => setSubmitError(null)}
          >
            {submitError}
          </Notification>
        )}
      </Stack>
    </Container>
  );
}