import { useState, useEffect } from 'react';
import {
  Container,
  Button,
  Paper,
  Title,
  Text,
  Badge,
  Group,
  Stack,
  Loader,
  Alert,
  Divider,
  Card,
  Grid,
  ActionIcon,
  Tooltip,
  TextInput,
  Collapse,
  Table,
  ScrollArea,
  Modal,
} from '@mantine/core';
import { 
  IconUser, 
  IconCalendar, 
  IconHash, 
  IconAlertCircle, 
  IconRefresh, 
  IconArrowLeft, 
  IconDownload, 
  IconMusic,
  IconUpload, 
  IconEdit, 
  IconCheck, 
  IconX, 
  IconPilcrow,
  IconHistory,
  IconChevronDown,
  IconChevronUp,
  //TODO[SC-262]: Uncomment these for the diff viewer
  // IconGitCompare,
  // IconEye,
} from '@tabler/icons-react';
import { apiService } from '../../services/apiService';
import { useParams, Link, useNavigate } from 'react-router-dom';

import { ScoreTitlePreview } from "../../components/ScoreTitlePreview";
import type { Arrangement, EditableArrangementData, VersionHistoryItem } from '../../services/apiService';

import type { PreviewStyleName } from '../../components/ScoreTitlePreview';

export default function ArrangementDisplay() {
  const {arrangementId = 1} = useParams();
  const [arrangement, setArrangement] = useState<Arrangement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mvtNo, setMvtNo] = useState<string>("")

  const [selectedStyle, setSelectedStyle] = useState<PreviewStyleName>("broadway")

  // Edit mode states
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<EditableArrangementData>({
    ensemble: 0,
    title: '',
    subtitle: '',
    style: "broadway",
    composer: '',
    mvt_no: '',
  });
  const [saveLoading, setSaveLoading] = useState(false);

  const [rawMsczUrl, setRawMsczUrl] = useState<string>("");
  const [msczUrl, setMsczUrl] = useState<string>("");
  const [scoreUrl, setScoreUrl] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [audioActionLoading, setAudioActionLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState<boolean>(true);
  const [exportError, setExportError] = useState<boolean>(false);

  // Version history states
  const [versionHistory, setVersionHistory] = useState<VersionHistoryItem[]>([]);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [versionHistoryLoading, setVersionHistoryLoading] = useState(false);
  const [selectedVersionForDownload, setSelectedVersionForDownload] = useState<number | null>(null);
  const [versionDownloadModal, setVersionDownloadModal] = useState(false);
  const [versionDownloadLoading, setVersionDownloadLoading] = useState(false);
  const [versionDownloadLinks, setVersionDownloadLinks] = useState({
    rawMsczUrl: '',
    msczUrl: '',
    scoreUrl: '',
    exportLoading: false,
    exportError: false
  });

  //TODO[SC-262]: uncomment when new score diff is ready
  // Diff functionality states
  // const [diffModal, setDiffModal] = useState(false);
  // const [selectedFromVersion, setSelectedFromVersion] = useState<number | null>(null);
  // const [selectedToVersion, setSelectedToVersion] = useState<number | null>(null);
  // const [diffLoading, setDiffLoading] = useState(false);
  // const [diffUrl, setDiffUrl] = useState<string>('');
  // const [diffError, setDiffError] = useState<string>('');

  const audioState = arrangement?.latest_version?.audio_state ?? "none";

  const navigate = useNavigate();

  const pollAudioState = async (arrangementId: number) => {
    let done = false;

    while (!done) {
      await new Promise((r) => setTimeout(r, 1500));

      const data = await apiService.getArrangementById(arrangementId);

      const state = data.latest_version?.audio_state;

      if (state === "complete" || state === "error") {
        setArrangement(data); // update React once at the end
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
      setAudioUrl(data.mp3_link)
      setExportLoading(data.is_processing)
      setExportError(data.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch version download links');
    } finally {
      setLoading(false);
    }
  }

  const fetchVersionHistory = async (arrangementId: number) => {
    try {
      setVersionHistoryLoading(true);
      const history = await apiService.getVersionHistory(arrangementId);
      setVersionHistory(history);
    } catch (err) {
      console.error('Failed to fetch version history:', err);
    } finally {
      setVersionHistoryLoading(false);
    }
  };

  const handleVersionDownload = async (versionId: number) => {
    setSelectedVersionForDownload(versionId);
    setVersionDownloadModal(true);
    setVersionDownloadLoading(true);

    try {
      const data = await apiService.getDownloadLinksForVersion(versionId);
      setVersionDownloadLinks({
        rawMsczUrl: data.raw_mscz_url,
        msczUrl: data.processed_mscz_url,
        scoreUrl: data.score_parts_pdf_link,
        exportLoading: data.is_processing,
        exportError: data.error
      });
    } catch (err) {
      setVersionDownloadLinks(prev => ({ ...prev, exportError: true }));
    } finally {
      setVersionDownloadLoading(false);
    }
  };

  // const handleComputeDiff = async () => {
  //   if (!selectedFromVersion || !selectedToVersion) {
  //     setDiffError('Please select both versions to compare');
  //     return;
  //   }

  //   if (selectedFromVersion === selectedToVersion) {
  //     setDiffError('Please select two different versions');
  //     return;
  //   }

  //   try {
  //     setDiffLoading(true);
  //     setDiffError('');
  //     const diffData = await apiService.computeDiff(selectedFromVersion, selectedToVersion);
      
  //     // Poll for completion if diff is still processing
  //     if (diffData.status === 'pending' || diffData.status === 'in_progress') {
  //       const pollForDiff = async () => {
  //         const updatedDiff = await apiService.getDiff(diffData.id);
  //         if (updatedDiff.status === 'completed') {
  //           setDiffUrl(updatedDiff.file_url);
  //           setDiffLoading(false);
  //         } else if (updatedDiff.status === 'failed') {
  //           setDiffError(`Failed to compute diff: ${updatedDiff.error_msg}`);
  //           setDiffLoading(false);
  //         } else {
  //           // Continue polling
  //           setTimeout(pollForDiff, 1000);
  //         }
  //       };
  //       setTimeout(pollForDiff, 1000);
  //     } else if (diffData.status === 'completed') {
  //       setDiffUrl(diffData.file_url);
  //       setDiffLoading(false);
  //     } else if (diffData.status === 'failed') {
  //       setDiffError(`Failed to compute diff: ${diffData.error_msg}`);
  //       setDiffLoading(false);
  //     }
  //   } catch (err) {
  //     setDiffError(err instanceof Error ? err.message : 'Failed to compute diff - An unknown error occurred');
  //     setDiffLoading(false);
  //   } 
  // };

  // const handleShowDiff = () => {
  //   setDiffModal(true);
  //   setSelectedFromVersion(null);
  //   setSelectedToVersion(null);
  //   setDiffUrl('');
  //   setDiffError('');
  // };

  const fetchArrangement = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getArrangementById(id);
      setArrangement(data);
      setMvtNo(data.mvt_no)

      // Initialize edit data
      setEditData({
        ensemble: data.ensemble || 0,
        title: data.title || '',
        subtitle: data.subtitle || '',
        style: data.style,
        composer: data.composer || '',
        mvt_no: data.mvt_no || '',
      });

      if (data?.latest_version?.id) {
        await getDownloadLinks(data.latest_version.id);
      }

      // Fetch version history
      await fetchVersionHistory(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch arrangement');
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
      
      // Refresh the arrangement data
      await fetchArrangement(+arrangementId);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleCancelEdit = () => {
    if (arrangement) {
      // Reset edit data to original values
      setEditData({
        ensemble: arrangement.ensemble || 0,
        title: arrangement.title || '',
        subtitle: arrangement.subtitle || '',
        style: arrangement.style,
        composer: arrangement.composer || '',
        mvt_no: arrangement.mvt_no || '',
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
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <Container size="md" py="xl">
        <Paper shadow="sm" p="xl" radius="md">
          <Group justify="center">
            <Loader size="xl" />
            <Text size="lg">Loading arrangement...</Text>
          </Group>
        </Paper>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="md" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
          {error}
          <Group mt="sm">
            <ActionIcon variant="light" color="red" onClick={handleRefresh}>
              <IconRefresh size={16} />
            </ActionIcon>
          </Group>
        </Alert>
      </Container>
    );
  }

  if (!arrangement) {
    return (
      <Container size="md" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} title="Not Found" color="orange">
          Arrangement not found.
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <Paper shadow="sm" p="xl" radius="md">
        <Group justify="space-between" mb="lg">
          <div>
            <Stack gap="xs">
              <Group gap="sm">
                <Button
                  variant="subtle"
                  leftSection={<IconArrowLeft size={16} />}
                  onClick={handleBackClick}
                >
                  Back to Arrangements
                </Button>
              </Group>
            </Stack>
            
            {isEditing ? (
              <>
                <TextInput
                  value={editData.title}
                  onChange={(event) => setEditData(prev => ({ ...prev, title: event.target.value }))}
                  size="xl"
                  variant="unstyled"
                  styles={{
                    input: {
                      fontSize: '2rem',
                      fontWeight: 700,
                      padding: 0,
                    }
                  }}
                  placeholder="Arrangement title"
                  mb="xs"
                />
                <TextInput
                  value={editData.subtitle}
                  onChange={(event) => setEditData(prev => ({ ...prev, subtitle: event.target.value }))}
                  size="lg"
                  variant="unstyled"
                  c="dimmed"
                  style={{ fontStyle: 'italic' }}
                  placeholder="Arrangement subtitle"
                  mb="xs"
                />
              </>
            ) : (
              <>
                <Title order={1} mb="xs">
                  {arrangement.mvt_no}: {arrangement.title}
                </Title>
                <Text size="lg" c="dimmed" mb="xs" fw={500} style={{ fontStyle: 'italic' }}>
                  {arrangement.subtitle}
                </Text>
              </>
            )}
            
            <Group gap="xs">
              <Badge variant="light" color="blue">
                ID: {arrangement.id}
              </Badge>
              <Badge variant="light" color="green">
                Ensemble: {arrangement.ensemble_name}
              </Badge>
            </Group>
          </div>
          
          <Group gap="xs">
            {isEditing ? (
              <>
                <Tooltip label="Save changes">
                  <ActionIcon 
                    variant="light" 
                    size="lg" 
                    color="green"
                    onClick={handleSaveChanges}
                    loading={saveLoading}
                  >
                    <IconCheck size={20} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Cancel editing">
                  <ActionIcon 
                    variant="light" 
                    size="lg" 
                    color="red"
                    onClick={handleCancelEdit}
                    disabled={saveLoading}
                  >
                    <IconX size={20} />
                  </ActionIcon>
                </Tooltip>
              </>
            ) : (
              <>
                <Tooltip label="Edit arrangement">
                  <ActionIcon 
                    variant="light" 
                    size="lg" 
                    color="blue"
                    onClick={() => setIsEditing(true)}
                  >
                    <IconEdit size={20} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Refresh data">
                  <ActionIcon variant="light" size="lg" onClick={handleRefresh}>
                    <IconRefresh size={20} />
                  </ActionIcon>
                </Tooltip>
              </>
            )}
          </Group>
        </Group>

        <Divider my="lg" />

        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="xs" padding="lg" radius="md" withBorder>
              <Stack gap="md">
                <Group>
                  <IconUser size={20} color="gray" />
                  <div style={{ flex: 1 }}>
                    <Text size="sm" c="dimmed">Composer</Text>
                    {isEditing ? (
                      <TextInput
                        value={editData.composer}
                        onChange={(event) => setEditData(prev => ({ ...prev, composer: event.target.value }))}
                        placeholder="Composer name"
                        variant="unstyled"
                        styles={{
                          input: {
                            fontWeight: 500,
                            padding: 0,
                          }
                        }}
                      />
                    ) : (
                      <Text fw={500}>
                        {arrangement.composer || 'Unknown'}
                      </Text>
                    )}
                  </div>
                </Group>

                <Group>
                  <IconHash size={20} color="gray" />
                  <div style={{ flex: 1 }}>
                    <Text size="sm" c="dimmed">Score Number</Text>
                    {isEditing ? (
                      <TextInput
                        value={mvtNo}
                        onChange={(e) => setMvtNo(e.currentTarget.value)}
                        placeholder="eg. '12' or '1-3' or '2m5'"
                        variant="unstyled"
                        styles={{
                          input: {
                            fontWeight: 500,
                            padding: 0,
                          }
                        }}
                      />
                    ) : (
                      <Text fw={500}>{arrangement.mvt_no}</Text>
                    )}
                  </div>
                </Group>

                <Group>
                  <IconPilcrow size={20} color="gray" />
                    <div style={{ flex: 1 }}>
                      <Text size="sm" c="dimmed">Style</Text>
                      <Text fw="500">{arrangement.style}</Text>
                    </div>
                </Group>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="xs" padding="lg" radius="md" withBorder>

              {isEditing ? (
                <ScoreTitlePreview
                  selectedStyle={selectedStyle}
                  setSelectedStyle={setSelectedStyle}
                  title={editData.title}
                  ensemble={arrangement.ensemble_name}
                  subtitle={editData.subtitle}
                  composer={editData.composer}
                  arranger={null}
                  mvtNo={mvtNo}
                  showTitle={arrangement.ensemble_name}
                  />
              ) : (
                <div id="nickId"> 
                <Title order={3} mb="md">Latest Version</Title>
                <Stack gap="md">
                  <Group>
                    <Badge variant="filled" color="teal" size="lg">
                      v{arrangement.latest_version_num || 'N/A'}
                    </Badge>
                    {/* Fix spacing of these buttons */}
                    <Button
                      component={Link}
                      to={`/app/arrangements/${arrangement.id}/new-version`}
                      variant={arrangement.latest_version ? "subtle" : "filled"}
                      size="sm"
                      rightSection={<IconUpload size={16} />}
                    >
                      Upload new Version
                    </Button>

                    {arrangement.latest_version && !exportLoading && !exportError && (
                    <>
                      <Button
                        onClick={handleAudioButtonClick}
                        variant="filled"
                        size="sm"
                        rightSection={<IconMusic size={16} />}
                        loading={audioState === "processing" || audioActionLoading}
                        disabled={audioState === "processing" || audioState === "error"}
                      >
                        {audioState === "none" && "Generate Audio"}
                        {audioState === "processing" && "Generating Audio…"}
                        {audioState === "complete" && "Play Midi Track"}
                        {audioState === "error" && "Audio Error"}
                      </Button>
                      <Button
                        component={Link}
                        target="_blank"
                        to={scoreUrl}
                        variant="filled"
                        size="sm"
                        rightSection={<IconDownload size={16} />} 
                      >
                        Download Score & Parts
                      </Button>
                      <Button
                        component={Link}
                        target="_blank"
                        to={msczUrl}
                        variant="filled"
                        size="sm"
                        rightSection={<IconDownload size={16} />} 
                      >
                        Download Formatted MSCZ file
                      </Button>
                      <Button
                        component={Link}
                        target="_blank"
                        to={rawMsczUrl}
                        variant="subtle"
                        size="sm"
                        rightSection={<IconDownload size={16} />}
                      >
                        Download Raw MSCZ file
                      </Button>
                    </>
                    )}

                    {exportLoading && (
                      <>
                        <Button
                          component={Link}
                          target="_blank"
                          to={rawMsczUrl}
                          variant="subtle"
                          size="sm"
                          rightSection={<IconDownload size={16} />}
                        >
                          Download Raw MSCZ file
                        </Button>
                        <Container>
                          <Group justify="center" py="xl">
                            <Loader size="md" />
                            <Text>Score Exporting...</Text>
                          </Group>
                        </Container>
                      </>
                    )}

                    {exportError && (
                      <>
                        <Button
                          component={Link}
                          target="_blank"
                          to={rawMsczUrl}
                          variant="subtle"
                          size="sm"
                          rightSection={<IconDownload size={16} />}
                        >
                          Download Raw MSCZ file
                        </Button>
                        <Container>
                          <Group justify="center" py="xl">
                            <Text>Error with Formatting. Tell Nick</Text>
                          </Group>
                        </Container>
                      </>
                    )}
                  </Group>

                  {arrangement.latest_version ? (
                    <>
                      <Group>
                        <IconCalendar size={20} color="gray" />
                        <div>
                          <Text size="sm" c="dimmed">Last Updated</Text>
                          <Text fw={500} size="sm">
                            {formatTimestamp(arrangement.latest_version.timestamp)}
                          </Text>
                        </div>
                      </Group>
                    </>
                  ) : (
                    <Alert icon={<IconAlertCircle size={16} />} color="gray" variant="light">
                      No version information available
                    </Alert>
                  )}
                </Stack>
              </div>
              )}
              
            </Card>
          </Grid.Col>
        </Grid>

        {/* Version History Section */}
        <Card shadow="xs" padding="lg" radius="md" withBorder mt="lg">
          <Group justify="space-between" mb="md">
            <Group>
              <IconHistory size={20} />
              <Title order={3}>Version History</Title>
              <Badge variant="light" color="blue">
                {versionHistory.length} versions
              </Badge>
            </Group>
            <Group>
              {/* //TODO[SC-262]: Uncomment to add back diff functionality
              <Button
                variant="light"
                color="orange"
                leftSection={<IconGitCompare size={16} />}
                onClick={handleShowDiff}
                disabled={versionHistory.length < 2}
              >
                Compare Versions
              </Button>
              */}
              <Button
                variant="subtle"
                rightSection={showVersionHistory ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                onClick={() => setShowVersionHistory(!showVersionHistory)}
                loading={versionHistoryLoading}
              >
                {showVersionHistory ? 'Hide' : 'Show'} History
              </Button>
            </Group>
          </Group>

          <Collapse in={showVersionHistory}>
            {versionHistory.length > 0 ? (
              <ScrollArea>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Version</Table.Th>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {versionHistory.map((version) => (
                      <Table.Tr key={version.id}>
                        <Table.Td>
                          <Text fw={version.is_latest ? 700 : 400}>
                            v{version.version_label}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">
                            {formatTimestamp(version.timestamp)}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Tooltip label="Download this version">
                              <ActionIcon
                                variant="light"
                                color="blue"
                                size="sm"
                                onClick={() => handleVersionDownload(version.id)}
                              >
                                <IconDownload size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            ) : (
              <Text c="dimmed" ta="center" py="xl">
                No version history available
              </Text>
            )}
          </Collapse>
        </Card>

        {/* Version Download Modal */}
        <Modal
          opened={versionDownloadModal}
          onClose={() => setVersionDownloadModal(false)}
          title={`Download Version ${versionHistory.find(v => v.id === selectedVersionForDownload)?.version_label || ''}`}
          size="lg"
        >
          {versionDownloadLoading ? (
            <Group justify="center" py="xl">
              <Loader size="md" />
              <Text>Loading download links...</Text>
            </Group>
          ) : versionDownloadLinks.exportError ? (
            <Alert icon={<IconAlertCircle size={16} />} color="red" mb="md">
              Error loading download links for this version
            </Alert>
          ) : versionDownloadLinks.exportLoading ? (
            <Group justify="center" py="xl">
              <Loader size="md" />
              <Text>This version is still processing...</Text>
            </Group>
          ) : (
            <Stack gap="md">
              <Text size="sm" c="dimmed">
                Choose which files to download for this version:
              </Text>
              
              <Group>
                <Button
                  component="a"
                  href={versionDownloadLinks.scoreUrl}
                  target="_blank"
                  variant="filled"
                  rightSection={<IconDownload size={16} />}
                  disabled={!versionDownloadLinks.scoreUrl}
                >
                  Score & Parts (PDF)
                </Button>
                
                <Button
                  component="a"
                  href={versionDownloadLinks.msczUrl}
                  target="_blank"
                  variant="filled"
                  rightSection={<IconDownload size={16} />}
                  disabled={!versionDownloadLinks.msczUrl}
                >
                  Formatted MSCZ
                </Button>
                
                <Button
                  component="a"
                  href={versionDownloadLinks.rawMsczUrl}
                  target="_blank"
                  variant="subtle"
                  rightSection={<IconDownload size={16} />}
                  disabled={!versionDownloadLinks.rawMsczUrl}
                >
                  Raw MSCZ
                </Button>
              </Group>
            </Stack>
          )}
        </Modal>

        {/* Diff Comparison Modal */}
        {/*}
        <Modal
          opened={diffModal}
          onClose={() => setDiffModal(false)}
          title="Compare Versions"
          size="xl"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Select two versions to compare. The diff will show changes from the first version to the second version.
            </Text>
            
            {diffError && (
              <Alert icon={<IconAlertCircle size={16} />} color="red">
                {diffError}
              </Alert>
            )}

            <Grid>
              <Grid.Col span={6}>
                <Text fw={500} mb="sm">From Version</Text>
                <Stack gap="xs">
                  {versionHistory.map((version) => (
                    <Button
                      key={version.id}
                      variant={selectedFromVersion === version.id ? "filled" : "light"}
                      color={selectedFromVersion === version.id ? "blue" : "gray"}
                      onClick={() => setSelectedFromVersion(version.id)}
                      fullWidth
                      justify="space-between"
                    >
                      <Text>v{version.version_label}</Text>
                      <Text size="xs" c="dimmed">
                        {new Date(version.timestamp).toLocaleDateString()}
                      </Text>
                    </Button>
                  ))}
                </Stack>
              </Grid.Col>

              <Grid.Col span={6}>
                <Text fw={500} mb="sm">To Version</Text>
                <Stack gap="xs">
                  {versionHistory.map((version) => (
                    <Button
                      key={version.id}
                      variant={selectedToVersion === version.id ? "filled" : "light"}
                      color={selectedToVersion === version.id ? "blue" : "gray"}
                      onClick={() => setSelectedToVersion(version.id)}
                      fullWidth
                      justify="space-between"
                    >
                      <Text>v{version.version_label}</Text>
                      <Text size="xs" c="dimmed">
                        {new Date(version.timestamp).toLocaleDateString()}
                      </Text>
                    </Button>
                  ))}
                </Stack>
              </Grid.Col>
            </Grid>

            <Group justify="space-between" mt="lg">
              <Button
                variant="light"
                color="orange"
                leftSection={<IconGitCompare size={16} />}
                onClick={handleComputeDiff}
                loading={diffLoading}
                disabled={!selectedFromVersion || !selectedToVersion || selectedFromVersion === selectedToVersion}
              >
                {diffLoading ? 'Computing Diff...' : 'Compute Diff'}
              </Button>

              {diffUrl && (
                <Button
                  component="a"
                  href={diffUrl}
                  target="_blank"
                  variant="filled"
                  color="green"
                  leftSection={<IconEye size={16} />}
                >
                  View Diff (PDF)
                </Button>
              )}
            </Group>

            {diffLoading && (
              <Group justify="center" py="md">
                <Loader size="sm" />
                <Text size="sm" c="dimmed">
                  Computing diff... This may take a moment.
                </Text>
              </Group>
            )}
          </Stack>
        </Modal>
        */}

        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Title order={3} mb="md">Download Parts</Title>
          <Text> Coming soon !</Text>
        </Card>
      </Paper>
    </Container>
  );
}