import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Title,
  Card,
  Text,
  Badge,
  Button,
  Group,
  Stack,
  Loader,
  Alert,
  Breadcrumbs,
  Anchor,
  Table,
  ActionIcon,
  Tooltip
} from '@mantine/core';
import { IconMusic, IconArrowLeft, IconEdit, IconUpload } from '@tabler/icons-react';
import { apiService } from '../../services/apiService';

const ArrangementsPage = () => {
  const { slug = "NA"} = useParams(); // Get ensemble slug from URL
  const navigate = useNavigate();
  const [ensemble, setEnsemble] = useState<any>(null);
  const [arrangements, setArrangements] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch both ensemble details and arrangements
        const [ensembleData] = await Promise.all([
          apiService.getEnsemble(slug),
        ]);
        setEnsemble(ensembleData);
        setArrangements(ensembleData.arrangements);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    if (slug) {
      fetchData();
    }
  }, [slug]);

  const handleBackClick = () => {
    navigate('/app/ensembles');
  };

  if (loading) {
    return (
      <Container>
        <Group justify="center" py="xl">
          <Loader size="lg" />
          <Text>Loading arrangements...</Text>
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert color="red" title="Error loading arrangements">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!ensemble) {
    return (
      <Container>
        <Alert color="yellow" title="Ensemble not found">
          The ensemble you're looking for doesn't exist.
        </Alert>
      </Container>
    );
  }

  const breadcrumbItems = [
    { title: 'Home', to: '/app' },
    { title: 'Ensembles', to: '/app/ensembles' },
    { title: ensemble.name, to: null }
  ].map((item, index) =>
    item.to ? (
      <Anchor
        key={index}
        component={Link}
        to={item.to}
        c="blue"
      >
        {item.title}
      </Anchor>
    ) : (
      <Anchor
        key={index}
        c="dimmed"
      >
        {item.title}
      </Anchor>
    )
  );

  return (
    <Stack gap="lg">
      <Breadcrumbs>{breadcrumbItems}</Breadcrumbs>
      
      <Group justify="space-between" align="flex-end">
        <Stack gap="xs">
          <Group gap="sm">
            <Button
              variant="subtle"
              leftSection={<IconArrowLeft size={16} />}
              onClick={handleBackClick}
            >
              Back to Ensembles
            </Button>
          </Group>
          <Title order={1}>{ensemble.name} - Arrangements</Title>
        </Stack>
        <Group>
          <Text c="dimmed">
            {arrangements.length} arrangement{arrangements.length !== 1 ? 's' : ''}
          </Text>
          <Button
            component={Link}
            to={`/app/ensembles/${ensemble.slug}/create-arrangement`}
            variant="filled"
            size="sm"
            rightSection={<ActionIcon size={16} />}
          >
            Create Arrangement
          </Button>
        </Group>
      </Group>

      {arrangements.length > 0 ? (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Movement #</Table.Th>
                <Table.Th>Title</Table.Th>
                <Table.Th>Composer</Table.Th>
                <Table.Th>Latest Version</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {arrangements.map((arrangement) => (
                <Table.Tr key={arrangement.id}>
                  <Table.Td>
                    <Badge variant="outline" size="sm">
                      {arrangement.mvt_no}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={500}><a href={`/app/arrangements/${arrangement.id}/new-version`}>{arrangement.title}</a></Text>
                  </Table.Td>
                  <Table.Td>
                    <Text c="dimmed" size="sm">
                      {arrangement.composer || '—'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      variant="light"
                      color={arrangement.latest_version_num !== 'N/A' ? 'green' : 'gray'}
                      size="sm"
                    >
                      v{arrangement.latest_version_num}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Tooltip label="Upload New Version">
                        <ActionIcon
                          variant="subtle"
                          color="blue"
                          component={Link}
                          to={`/app/arrangements/${arrangement.id}/new-version`} //TODO: Have this link to the right spot
                        >
                          <IconUpload size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Give Feedback">
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          component={Link}
                          to={`/app/arrangements/${arrangement.slug}/feedback`}
                        >
                          <IconEdit size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      ) : (
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack align="center" gap="md">
            <IconMusic size={48} color="var(--mantine-color-gray-5)" />
            <Text size="lg" c="dimmed">No arrangements found</Text>
            <Text size="sm" c="dimmed" ta="center">
              This ensemble doesn't have any arrangements yet. Add your first arrangement to get started.
            </Text>
            <Button variant="light" component={Link} to={`/app/ensembles/${ensemble.slug}/create-arrangement`}>Add New Arrangement</Button>
          </Stack>
        </Card>
      )}
    </Stack>
  );
};

export default ArrangementsPage;