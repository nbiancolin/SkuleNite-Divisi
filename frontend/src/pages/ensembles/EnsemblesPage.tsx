import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Container,
  Title,
  Card,
  Text,
  Grid,
  Badge,
  Button,
  Group,
  Stack,
  Loader,
  Alert
} from '@mantine/core';
import { IconMusic, IconEye } from '@tabler/icons-react';
import { apiService } from '../../services/apiService';

const EnsemblesPage = () => {
  const [ensembles, setEnsembles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    const fetchEnsembles = async () => {
      try {
        setLoading(true);
        const data = await apiService.getEnsembles();
        setEnsembles(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchEnsembles();
  }, []);

  if (loading) {
    return (
      <Container>
        <Group justify="center" py="xl">
          <Loader size="lg" />
          <Text>Loading ensembles...</Text>
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert color="red" title="Error loading ensembles">
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end">
        <Title order={1}>Ensembles</Title>
        <Text c="dimmed">{ensembles.length} ensemble{ensembles.length !== 1 ? 's' : ''}</Text>
      </Group>

      <Grid>
        {ensembles.map((ensemble) => (
          <Grid.Col key={ensemble.id} span={{ base: 12, sm: 6, lg: 4 }}>
            <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
              <Stack gap="md" h="100%">
                <Group gap="xs">
                  <IconMusic size={20} color="var(--mantine-color-blue-6)" />
                  <Title order={3}>{ensemble.name}</Title>
                </Group>

                <Text c="dimmed" size="sm" flex={1}>
                  {ensemble.arrangements?.length || 0} arrangement{ensemble.arrangements?.length !== 1 ? 's' : ''}
                </Text>

                <Group justify="space-between" mt="auto">
                  <Badge variant="light" color="blue">
                    {ensemble.slug}
                  </Badge>
                  <Button
                    component={Link}
                    to={`/app/ensembles/${ensemble.slug}/arrangements`}
                    variant="filled"
                    size="sm"
                    rightSection={<IconEye size={16} />}
                  >
                    View Arrangements
                  </Button>
                </Group>
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>

      {ensembles.length === 0 && (
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack align="center" gap="md">
            <IconMusic size={48} color="var(--mantine-color-gray-5)" />
            <Text size="lg" c="dimmed">No ensembles found</Text>
            <Text size="sm" c="dimmed" ta="center">
              Create your first ensemble to get started with managing your musical arrangements.
            </Text>
          </Stack>
        </Card>
      )}
    </Stack>
  );
};

export default EnsemblesPage;