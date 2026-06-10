import { useState, useEffect, useCallback } from 'react';
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
  Tooltip,
  TextInput,
  Tabs,
} from '@mantine/core';
import { IconMusic, IconArrowLeft, IconEdit, IconUpload, IconLink, IconCopy, IconCheck, IconAlertCircle, IconMessageCircle } from '@tabler/icons-react';
import { apiService, type Ensemble, type PartName, type Arrangement } from '../../services/apiService';
import { usePageTitle } from '../../context/usePageTitle';
import { EnsemblePartBooksSection } from './EnsemblePartBooksSection';

const ArrangementsPage = () => {
  const { slug = "NA" } = useParams(); // Get ensemble slug from URL
  const navigate = useNavigate();
  const [ensemble, setEnsemble] = useState<Ensemble | null>(null);
  usePageTitle(ensemble ? `${ensemble.name} - Arrangements` : null);
  const [arrangements, setArrangements] = useState<Arrangement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [inviteLinkLoading, setInviteLinkLoading] = useState(false);
  const [partBookError, setPartBookError] = useState<string | null>(null);

  const [copied, setCopied] = useState(false);

  const fetchData = useCallback(async (quiet = false) => {
    if (!slug) return;
    try {
      if (!quiet) setLoading(true);
      const [ensembleData, arrangementData] = await Promise.all([
        apiService.getEnsemble(slug),
        apiService.getEnsembleArrangements(slug),
      ]);
      setEnsemble(ensembleData);
      setArrangements(arrangementData);
    } catch (err) {
      if (!quiet && err instanceof Error) {
        setError(err.message);
      }
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    if (slug) fetchData();
  }, [slug, fetchData]);

  // Poll while part books are generating (quiet refetch so we don't show full-page loader)
  useEffect(() => {
    if (!slug || !ensemble?.part_books_generating) return;
    const interval = setInterval(() => fetchData(true), 3000);
    return () => clearInterval(interval);
  }, [slug, ensemble?.part_books_generating, fetchData]);

  const handleBackClick = () => {
    navigate('/app/ensembles');
  };

  const handleGetInviteLink = async () => {
    if (!ensemble) return;
    try {
      setInviteLinkLoading(true);
      const data = await apiService.getInviteLink(ensemble.slug);
      setInviteLink(data.join_url);
      setEnsemble({ ...ensemble, join_link: data.join_url });
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setInviteLinkLoading(false);
    }
  };

  const handleCopyLink = async () => {
    const linkToCopy = inviteLink || ensemble?.join_link;
    if (linkToCopy) {
      await navigator.clipboard.writeText(linkToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
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

  const partNames: PartName[] = (() => {
    const raw = ensemble.part_names
      ?? (ensemble as { part_name?: PartName[] }).part_name
      ?? [];
    if (!Array.isArray(raw)) return [];
    return raw.filter(
      (p): p is PartName =>
        p != null &&
        typeof p === 'object' &&
        typeof p.id === 'number' &&
        typeof p.display_name === 'string'
    );
  })();

  const breadcrumbItems = [
    { title: 'Home', to: '/app' },
    { title: 'Ensembles', to: '/app/ensembles' },
    { title: ensemble.name, to: `/app/ensembles/${ensemble.slug}` }
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
        component={Link}
        to={item.to}
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
              Back to Arrangements
            </Button>
          </Group>
          <Title order={1}>{ensemble.name} - Arrangements</Title>
        </Stack>
        <Group>
          <Text c="dimmed">
            {arrangements.length} arrangement{arrangements.length !== 1 ? 's' : ''}
          </Text>
          {ensemble.is_admin && (
            <Group gap="xs">
              {ensemble.join_link || inviteLink ? (
                <Group gap="xs">
                  <TextInput
                    value={inviteLink || ensemble.join_link || ''}
                    readOnly
                    size="sm"
                    style={{ width: '300px' }}
                  />
                  <Tooltip label={copied ? "Copied!" : "Copy link"}>
                    <ActionIcon
                      variant="light"
                      color={copied ? "green" : "blue"}
                      onClick={handleCopyLink}
                    >
                      {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                    </ActionIcon>
                  </Tooltip>
                </Group>
              ) : (
                <Button
                  variant="light"
                  size="sm"
                  leftSection={<IconLink size={16} />}
                  onClick={handleGetInviteLink}
                  loading={inviteLinkLoading}
                >
                  Get Invite Link
                </Button>
              )}
            </Group>
          )}
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

      {partBookError && (
        <Alert color="red" title="Part Book Generation Failed">
          {partBookError}
        </Alert>
      )}

      <Tabs defaultValue="arrangements" mt="md">
        <Tabs.List>
          <Tabs.Tab value="arrangements">
            Arrangements
            <Badge size="sm" variant="light" ml="xs">{arrangements.length}</Badge>
          </Tabs.Tab>
          <Tabs.Tab value="parts">
            Parts & part books
            <Badge size="sm" variant="light" ml="xs">{partNames.length}</Badge>
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="arrangements" pt="md">
          {arrangements.length > 0 ? (
            <Card shadow="sm" padding="lg" radius="md" withBorder>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Movement #</Table.Th>
                    <Table.Th>Title</Table.Th>
                    <Table.Th>Latest Version</Table.Th>
                    <Table.Th>Commit</Table.Th>
                    <Table.Th>Comments</Table.Th>
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
                        <Text fw={500}><a href={`/app/arrangements/${arrangement.id}/`}>{arrangement.title}</a></Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          variant="light"
                          color={
                            arrangement.latest_version_num !== 'N/A'
                              ? arrangement.latest_version_num.startsWith('0')
                                ? 'yellow'
                                : 'green'
                              : 'gray'
                          }
                          size="sm"
                        >
                          v{arrangement.latest_version_num}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {arrangement.has_unversioned_latest_commit ? (
                          <Tooltip label="Latest commit has not been turned into a version yet">
                            <Badge
                              variant="light"
                              color="orange"
                              size="sm"
                              leftSection={<IconAlertCircle size={12} />}
                            >
                              Unversioned commit
                            </Badge>
                          </Tooltip>
                        ) : (
                          <Text c="dimmed" size="sm">—</Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {arrangement.has_unresolved_comments_on_latest_version ? (
                          <Tooltip label="Latest version has unresolved comments">
                            <Badge
                              variant="light"
                              color="orange"
                              size="sm"
                              leftSection={<IconMessageCircle size={12} />}
                            >
                              Unresolved comments
                            </Badge>
                          </Tooltip>
                        ) : (
                          <Text c="dimmed" size="sm">—</Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Tooltip label="Upload New File">
                            <ActionIcon
                              variant="subtle"
                              color="blue"
                              component={Link}
                              to={`/app/arrangements/${arrangement.id}/new-commit`}
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
        </Tabs.Panel>

        <Tabs.Panel value="parts" pt="md">
          <EnsemblePartBooksSection
            ensemble={ensemble}
            partNames={partNames}
            onRefresh={() => fetchData(true)}
            onError={(message) => setPartBookError(message)}
          />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};

export default ArrangementsPage;