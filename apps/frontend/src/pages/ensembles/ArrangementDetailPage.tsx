import {
  Container,
  Button,
  Menu,
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
  IconGitCommit,
  IconMessageCircle,
} from '@tabler/icons-react';
import { Link } from 'react-router-dom';

import { ScoreTitlePreview } from "../../components/ScoreTitlePreview";
import { useArrangementDetailPage } from "./useArrangementDetailPage";

export default function ArrangementDisplay() {
  const {
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
    audioActionLoading,
    exportLoading,
    exportError,
    versionHistory,
    showVersionHistory,
    setShowVersionHistory,
    versionHistoryLoading,
    selectedVersionForDownload,
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
    arrangementId,
  } = useArrangementDetailPage();

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
                    <Group wrap="nowrap" gap={0}>
                      <Button
                        component={Link}
                        to={`/app/arrangements/${arrangement.id}/new-commit`}
                        variant={arrangement.latest_version ? "subtle" : "filled"}
                        size="sm"
                        rightSection={<IconUpload size={16} />}
                      >
                        Upload new file
                      </Button>
                      <Menu transitionProps={{ transition: 'pop' }} position="bottom-end" withinPortal>
                        <Menu.Target>
                          <ActionIcon
                            variant={arrangement.latest_version ? "subtle" : "filled"}
                            size={36}
                            aria-label="More options"
                          >
                            <IconChevronDown size={16} stroke={1.5} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item
                            component={Link}
                            to={`/app/arrangements/${arrangement.id}/new-version`}
                            leftSection={<IconCalendar size={16} stroke={1.5}/>}
                          >
                            Directly Create Version
                          </Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Group>
                    {arrangement.latest_version && !exportLoading && !exportError && (
                    <>
                      <Button
                        component={Link}
                        to={`/app/arrangements/${arrangement.id}/review-score?version_id=${arrangement.latest_version.id}`}
                        variant="light"
                        size="sm"
                        rightSection={<IconMessageCircle size={16} />}
                      >
                        Review Score
                      </Button>
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
                        component="a"
                        href={allPartsUrl || undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        variant="light"
                        size="sm"
                        rightSection={<IconDownload size={16} />}
                        disabled={!allPartsUrl}
                      >
                        Download all parts
                      </Button>
                      <Group wrap="nowrap" gap={0}>
                      <Button
                        component="a"
                        href={canDownloadLatestCommitMscz ? latestCommitMsczDownloadUrl : undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        variant={arrangement.latest_version ? "subtle" : "filled"}
                        size="sm"
                        rightSection={<IconDownload size={16} />}
                        disabled={!canDownloadLatestCommitMscz}
                      >
                        Download Latest commit mscz
                      </Button>
                      <Menu transitionProps={{ transition: 'pop' }} position="bottom-end" withinPortal>
                        <Menu.Target>
                          <ActionIcon
                            variant={arrangement.latest_version ? "subtle" : "filled"}
                            size={36}
                            aria-label="More options"
                          >
                            <IconChevronDown size={16} stroke={1.5} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item
                            component={Link}
                            to={msczUrl}
                            disabled={msczUrl === ''}
                          >
                            Download Latest Formatted Version mscz
                          </Menu.Item>
                          <Menu.Item
                            component={Link}
                            to={rawMsczUrl}
                            disabled={rawMsczUrl === ''}
                          >
                            Download Latest Raw Version mscz
                          </Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Group>
                    </>
                    )}

                    {exportLoading && (
                      <>
                        <Button
                          component="a"
                          href={canDownloadLatestCommitMscz ? latestCommitMsczDownloadUrl : undefined}
                          target="_blank"
                          rel="noopener noreferrer"
                          variant="subtle"
                          size="sm"
                          rightSection={<IconDownload size={16} />}
                          disabled={!canDownloadLatestCommitMscz}
                        >
                          Download MSCZ from latest commit
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
                          component="a"
                          href={canDownloadLatestCommitMscz ? latestCommitMsczDownloadUrl : undefined}
                          target="_blank"
                          rel="noopener noreferrer"
                          variant="subtle"
                          size="sm"
                          rightSection={<IconDownload size={16} />}
                          disabled={!canDownloadLatestCommitMscz}
                        >
                          Download MSCZ from latest commit
                        </Button>
                        <Container>
                          <Group justify="center" py="xl">
                            <Text>Error with Formatting. Tell Nick</Text>
                          </Group>
                        </Container>
                      </>
                    )}

                    {!arrangement.latest_version && canDownloadLatestCommitMscz && (
                      <Button
                        component="a"
                        href={latestCommitMsczDownloadUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        variant="subtle"
                        size="sm"
                        rightSection={<IconDownload size={16} />}
                      >
                        Download MSCZ from latest commit
                      </Button>
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

        <Card shadow="xs" padding="lg" radius="md" withBorder mt="lg">
          <Group justify="space-between" mb="md">
            <Group>
              <IconGitCommit size={20} />
              <Title order={3}>Latest Commits</Title>
              <Badge variant="light" color="grape">
                {commits.length} commits
              </Badge>
            </Group>
            <Button
              variant="subtle"
              rightSection={showCommitHistory ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
              onClick={() => setShowCommitHistory(!showCommitHistory)}
              loading={commitsLoading}
            >
              {showCommitHistory ? 'Hide' : 'Show'} Commits
            </Button>
          </Group>

          <Collapse in={showCommitHistory}>
            {commits.length > 0 ? (
              <ScrollArea>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>id</Table.Th>
                      <Table.Th>Message</Table.Th>
                      <Table.Th>Created By</Table.Th>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {commits.map((commit) => (
                      <Table.Tr key={commit.id}>
                        <Table.Td>
                          <Text ff="monospace">{commit.id}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{commit.message || "(no message)"}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">
                            {commit.created_by?.username || "-"}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{formatTimestamp(commit.timestamp)}</Text>
                        </Table.Td>
                        <Table.Td>
                          {commit.has_version ? (
                            <Badge color="green" variant="light">Version created</Badge>
                          ) : (
                            <Button
                              component={Link}
                              to={`/app/arrangements/${arrangementId}/commits/${commit.id}/create-version`}
                              size="xs"
                              variant="light"
                            >
                              Create Version
                            </Button>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            ) : (
              <Text c="dimmed" ta="center" py="xl">
                No commit history available
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
                  Download Formatted MSCZ
                </Button>
                <Button
                  component="a"
                  href={versionDownloadLinks.rawMsczUrl}
                  target="_blank"
                  variant="filled"
                  rightSection={<IconDownload size={16} />}
                  disabled={!versionDownloadLinks.rawMsczUrl}
                >
                  Download Raw MSCZ
                </Button>
              </Group>

              {/* Individual Parts Section */}
              {partsLoading ? (
                <Group justify="center" py="md">
                  <Loader size="sm" />
                  <Text size="sm" c="dimmed">Loading parts...</Text>
                </Group>
              ) : parts.length > 0 ? (
                <>
                  <Divider label="Individual Parts" labelPosition="center" my="md" />
                  <Text size="sm" c="dimmed" mb="xs">
                    Download individual part PDFs:
                  </Text>
                  <ScrollArea h={300}>
                    <Stack gap="xs">
                      {parts.map((part) => {
                        const downloadUrl = part.file_url || part.download_url;
                        return (
                          <Button
                            key={part.id}
                            component="a"
                            href={downloadUrl}
                            target="_blank"
                            variant={part.is_score ? "light" : "subtle"}
                            fullWidth
                            justify="space-between"
                            rightSection={<IconDownload size={16} />}
                            disabled={!downloadUrl}
                          >
                            <Group gap="xs">
                              {part.is_score && <IconMusic size={16} />}
                              <Text>{part.name}</Text>
                            </Group>
                          </Button>
                        );
                      })}
                    </Stack>
                  </ScrollArea>
                </>
              ) : !versionDownloadLinks.exportLoading && !versionDownloadLinks.exportError ? (
                <Text size="sm" c="dimmed" mt="md">
                  No individual parts available for this version.
                </Text>
              ) : null}
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
          {latestVersionPartsLoading ? (
            <Group justify="center" py="md">
              <Loader size="sm" />
              <Text size="sm" c="dimmed">Loading parts...</Text>
            </Group>
          ) : latestVersionParts.length > 0 ? (
            <Stack gap="xs" mt="sm">
              <Text size="sm" c="dimmed" mb="xs">
                Download individual part PDFs from the latest version:
              </Text>
              <ScrollArea h={400}>
                <Stack gap="xs">
                  {latestVersionParts.map((part) => {
                    const downloadUrl = part.file_url || part.download_url;
                    return (
                      <Button
                        key={part.id}
                        component="a"
                        href={downloadUrl}
                        target="_blank"
                        variant={part.is_score ? "light" : "subtle"}
                        fullWidth
                        justify="space-between"
                        rightSection={<IconDownload size={16} />}
                        disabled={!downloadUrl}
                      >
                        <Group gap="xs">
                          {part.is_score && <IconMusic size={16} />}
                          <Text>{part.name}</Text>
                        </Group>
                      </Button>
                    );
                  })}
                </Stack>
              </ScrollArea>
            </Stack>
          ) : arrangement?.latest_version ? (
            <Text size="sm" c="dimmed" mt="sm">
              No parts available for the latest version yet. Parts will appear here after the version is exported.
            </Text>
          ) : (
            <Text size="sm" c="dimmed" mt="sm">
              No latest version available. Upload a version to see parts here.
            </Text>
          )}
        </Card>
      </Paper>
    </Container>
  );
}