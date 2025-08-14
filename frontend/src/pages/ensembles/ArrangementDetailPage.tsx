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
} from '@mantine/core';
import { IconMusic, IconUser, IconCalendar, IconHash, IconAlertCircle, IconRefresh, IconArrowLeft, IconDownload, IconUpload } from '@tabler/icons-react';
import { apiService } from '../../services/apiService';
import { useParams, Link, useNavigate } from 'react-router-dom';

import type { Arrangement } from '../../services/apiService';

export default function ArrangementDisplay() {
  const {arrangementId = 1} = useParams()
  const [arrangement, setArrangement] = useState<Arrangement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [rawMsczUrl, setRawMsczUrl] = useState<string>("");
  const [msczUrl, setMsczUrl] = useState<string>("");
  const [scoreUrl, setScoreUrl] = useState<string>("");
  const [exportLoading, setExportLoading] = useState<boolean>(true);
  const [exportError, setExportError] = useState<boolean>(false);

  const navigate = useNavigate()

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

  const fetchArrangement = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getArrangementById(id);
      setArrangement(data);

      if (data?.latest_version?.id) {
        await getDownloadLinks(data.latest_version.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch arrangement');
    } finally {
      setLoading(false);
    }
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
            <Title order={1} mb="xs">
              {arrangement.mvt_no}: {arrangement.title}
            </Title>
            <Group gap="xs">
              <Badge variant="light" color="blue">
                ID: {arrangement.id}
              </Badge>
              <Badge variant="light" color="green">
                Ensemble: {arrangement.ensemble_name}
              </Badge>
            </Group>
          </div>
          <Tooltip label="Refresh data">
            <ActionIcon variant="light" size="lg" onClick={handleRefresh}>
              <IconRefresh size={20} />
            </ActionIcon>
          </Tooltip>
        </Group>

        <Divider my="lg" />

        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="xs" padding="lg" radius="md" withBorder>
              <Stack gap="md">
                <Group>
                  <IconUser size={20} color="gray" />
                  <div>
                    <Text size="sm" c="dimmed">Composer</Text>
                    <Text fw={500}>
                      {arrangement.composer || 'Unknown'}
                    </Text>
                  </div>
                </Group>

                <Group>
                  <IconMusic size={20} color="gray" />
                  <div>
                    <Text size="sm" c="dimmed">Movement</Text>
                    <Text fw={500}>{arrangement.mvt_no}</Text>
                  </div>
                </Group>

                {arrangement.actNumber && (
                  <Group>
                    <IconHash size={20} color="gray" />
                    <div>
                      <Text size="sm" c="dimmed">Act Number</Text>
                      <Text fw={500}>{arrangement.actNumber}</Text>
                    </div>
                  </Group>
                )}
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="xs" padding="lg" radius="md" withBorder>
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
                    rightSection={<IconDownload size={16} />}  //TOOD Fix icon here
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
            </Card>
          </Grid.Col>
        </Grid>

        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Title order={3} mb="md">Download Parts</Title>
          <Text> Coming soon !</Text>
        </Card>
      </Paper>
    </Container>
  );
}