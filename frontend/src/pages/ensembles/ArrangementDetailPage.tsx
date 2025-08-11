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
import { IconMusic, IconUser, IconCalendar, IconHash, IconAlertCircle, IconRefresh, IconUpload } from '@tabler/icons-react';
import { apiService } from '../../services/apiService';
import { useParams, Link } from 'react-router-dom';

// Import your API service types and functions
interface ArrangementVersion {
  id: number;
  uuid: string;
  arrangementId: number;
  versionNum: string;
  timestamp: string;
}

interface Arrangement {
  id: number;
  ensemble: number;
  title: string;
  slug: string;
  composer: string | null;
  actNumber: number | null;
  pieceNumber: number;
  mvt_no: string;
  latestVersion: ArrangementVersion;
  latestVersionNum: string;
}

export default function ArrangementDisplay() {
  const {arrangementId = 1} = useParams()
  const [arrangement, setArrangement] = useState<Arrangement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentId, setCurrentId] = useState(arrangementId);

  const fetchArrangement = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      // In real implementation, use: apiService.getArrangementById(id)
      const data = await apiService.getArrangementById(id);
      setArrangement(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch arrangement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArrangement(currentId);
  }, [currentId]);

  const handleRefresh = () => {
    fetchArrangement(currentId);
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
    <Container size="md" py="xl">
      <Paper shadow="sm" p="xl" radius="md">
        <Group justify="space-between" mb="lg">
          <div>
            <Title order={1} mb="xs">
              {arrangement.title}
            </Title>
            <Group gap="xs">
              <Badge variant="light" color="blue">
                ID: {arrangement.id}
              </Badge>
              <Badge variant="light" color="green">
                Ensemble: {arrangement.ensemble}
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

                <Group>
                  <IconHash size={20} color="gray" />
                  <div>
                    <Text size="sm" c="dimmed">Piece Number</Text>
                    <Text fw={500}>{arrangement.pieceNumber}</Text>
                  </div>
                </Group>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="xs" padding="lg" radius="md" withBorder>
              <Title order={3} mb="md">Latest Version</Title>
              <Stack gap="md">
                <Group>
                  <Badge variant="filled" color="teal" size="lg">
                    v{arrangement.latestVersionNum || 'N/A'}
                  </Badge>
                  <Button
                    component={Link}
                    to={`/app/ensembles/${arrangement.ensemble}/create-arrangement`}
                    variant="filled"
                    size="sm"
                    rightSection={<IconUpload size={16} />}
                  >
                    Create Arrangement
                  </Button>
                </Group>

                {arrangement.latestVersion ? (
                  <>
                    <div>
                      <Text size="sm" c="dimmed">Version UUID</Text>
                      <Text fw={500} size="sm" style={{ fontFamily: 'monospace' }}>
                        {arrangement.latestVersion.uuid}
                      </Text>
                    </div>

                    <Group>
                      <IconCalendar size={20} color="gray" />
                      <div>
                        <Text size="sm" c="dimmed">Last Updated</Text>
                        <Text fw={500} size="sm">
                          {formatTimestamp(arrangement.latestVersion.timestamp)}
                        </Text>
                      </div>
                    </Group>

                    <div>
                      <Text size="sm" c="dimmed">Version ID</Text>
                      <Text fw={500}>{arrangement.latestVersion.id}</Text>
                    </div>
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

        <Divider my="lg" />

        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Title order={3} mb="md">Technical Details</Title>
          <Group>
            <div>
              <Text size="sm" c="dimmed">Slug</Text>
              <Text fw={500} size="sm" style={{ fontFamily: 'monospace' }}>
                {arrangement.slug}
              </Text>
            </div>
          </Group>
        </Card>
      </Paper>
    </Container>
  );
}