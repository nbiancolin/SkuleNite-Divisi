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
  IconUpload, 
  IconEdit, 
  IconCheck, 
  IconX, 
  IconPilcrow,
  IconHistory,
  IconChevronDown,
  IconChevronUp,
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
    piece_number: undefined,
    act_number: undefined,
  });
  const [saveLoading, setSaveLoading] = useState(false);

  const [rawMsczUrl, setRawMsczUrl] = useState<string>("");
  const [msczUrl, setMsczUrl] = useState<string>("");
  const [scoreUrl, setScoreUrl] = useState<string>("");
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

  const navigate = useNavigate();

  const processMvtNo = (mvt_no: string) => {
    // split string at eithr - or m,
      // if neither present, return the whole thing as a number
    // first one is act number, second one is piece number

    if(mvt_no.includes("-")){
        const vals = mvt_no.split("-")
        editData.act_number = +vals[0]
        editData.piece_number = +vals[1]

    } else if (mvt_no.includes("m")) {
        const vals = mvt_no.split("m")
        editData.act_number = +vals[0]
        editData.piece_number = +vals[1]
    }
    else {
      //wrap in trycatch
      editData.piece_number = +mvt_no
      editData.act_number = null
    }
  }

  const getDownloadLinks = async (arrangementVersionId: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDownloadLinksForVersion(arrangementVersionId);
      setRawMsczUrl(data.raw_mscz_url);
      setMsczUrl(data.processed_mscz_url);
      setScoreUrl(data.score_parts_pdf_link);
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
        piece_number: data.piece_number,
        act_number: data.act_number,
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
      editData.style = selectedStyle
      processMvtNo(mvtNo)
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
        piece_number: arrangement.pieceNumber,
        act_number: arrangement.actNumber,
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
                  pieceNumber={null}
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
                      <Container>
                        <Group justify="center" py="xl">
                          <Loader size="md" />
                          <Text>Score Exporting...</Text>
                        </Group>
                      </Container>
                    )}

                    {exportError && (
                      <Container>
                        <Group justify="center" py="xl">
                          <Text>Error with Formatting. Tell Nick</Text>
                        </Group>
                      </Container>
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
            <Button
              variant="subtle"
              rightSection={showVersionHistory ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
              onClick={() => setShowVersionHistory(!showVersionHistory)}
              loading={versionHistoryLoading}
            >
              {showVersionHistory ? 'Hide' : 'Show'} History
            </Button>
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

        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Title order={3} mb="md">Download Parts</Title>
          <Text> Coming soon !</Text>
        </Card>
      </Paper>
    </Container>
  );
}