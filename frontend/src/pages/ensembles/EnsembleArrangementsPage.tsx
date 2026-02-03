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
  Tooltip,
  TextInput,
  Collapse,
  Divider,
  Tabs,
} from '@mantine/core';
import { IconMusic, IconArrowLeft, IconEdit, IconUpload, IconLink, IconCopy, IconCheck, IconBook, IconDownload, IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { apiService, type Ensemble, type EnsemblePartBook, type PartName } from '../../services/apiService';

const ArrangementsPage = () => {
  const { slug = "NA" } = useParams(); // Get ensemble slug from URL
  const navigate = useNavigate();
  const [ensemble, setEnsemble] = useState<Ensemble | null>(null);
  const [arrangements, setArrangements] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [inviteLinkLoading, setInviteLinkLoading] = useState(false);
  const [partBookLoading, setPartBookLoading] = useState(false);
  const [partBookError, setPartBookError] = useState<string | null>(null);

  const [copied, setCopied] = useState(false);
  const [expandedPartId, setExpandedPartId] = useState<number | null>(null);

  const fetchData = async (quiet = false) => {
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
  };

  useEffect(() => {
    if (slug) fetchData();
  }, [slug]);

  // Poll while part books are generating (quiet refetch so we don't show full-page loader)
  useEffect(() => {
    if (!slug || !ensemble?.part_books_generating) return;
    const interval = setInterval(() => fetchData(true), 3000);
    return () => clearInterval(interval);
  }, [slug, ensemble?.part_books_generating]);

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

  const handleGeneratePartBooks = async () => {
    if (!ensemble) return;

    try {
      setPartBookLoading(true);
      setPartBookError(null);
      await apiService.generatePartBooksForEnsemble(ensemble.slug);
      // Backend triggers async generation; refetch ensemble so UI shows part_books_generating (polling will update when done)
      const updated = await apiService.getEnsemble(ensemble.slug);
      setEnsemble(updated);
    } catch (err) {
      if (err instanceof Error) {
        setPartBookError(err.message);
      }
    } finally {
      setPartBookLoading(false);
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
    const raw = (ensemble as { part_names?: PartName[]; part_name?: PartName[] }).part_names
      ?? (ensemble as { part_names?: PartName[]; part_name?: PartName[] }).part_name
      ?? [];
    if (!Array.isArray(raw)) return [];
    return raw
      .map((p: PartName) => {
        if (p && typeof p === 'object' && typeof p.id === 'number' && typeof p.display_name === 'string') {
          return { id: p.id, display_name: p.display_name };
        }
        if (p && typeof p === 'object') {
          const entries = Object.entries(p);
          if (entries.length === 1) {
            const [idStr, name] = entries[0];
            const id = Number(idStr);
            if (Number.isFinite(id) && typeof name === 'string') return { id, display_name: name };
          }
        }
        return null;
      })
      .filter((x): x is PartName => x != null);
  })();

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
                        <Text fw={500}><a href={`/app/arrangements/${arrangement.id}/`}>{arrangement.title}</a></Text>
                      </Table.Td>
                      <Table.Td>
                        <Text c="dimmed" size="sm">
                          {arrangement.composer || '—'}
                        </Text>
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
                        <Group gap="xs">
                          <Tooltip label="Upload New Version">
                            <ActionIcon
                              variant="subtle"
                              color="blue"
                              component={Link}
                              to={`/app/arrangements/${arrangement.id}/new-version`}
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
          <Card shadow="sm" radius="md" withBorder>
            <Stack gap="sm">
              <Group justify="space-between">
                <Group gap="xs">
                  <IconBook size={20} />
                  <Text fw={500}>Parts & part books</Text>
                  {ensemble.part_books_generating && (
                    <Badge color="blue" variant="light">Generating…</Badge>
                  )}
                </Group>
                {ensemble.is_admin && (
                  <Button
                    size="sm"
                    variant="light"
                    leftSection={<IconBook size={16} />}
                    onClick={handleGeneratePartBooks}
                    loading={partBookLoading}
                    disabled={!!ensemble.part_books_generating || partNames.length === 0}
                  >
                    Generate part books
                  </Button>
                )}
              </Group>
              <Divider />
              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                {partNames.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    No part names yet. Part names are added when you upload arrangement versions with parts.
                  </Text>
                ) : (
                  <Stack gap={0} mt="xs">
                    {partNames
                      .slice()
                      .sort((a, b) => {
                        // Sort by order (nulls last), then by display_name for stable ordering
                        if (a.order !== null && b.order !== null) {
                          return a.order - b.order;
                        }
                        if (a.order !== null) return -1;
                        if (b.order !== null) return 1;
                        return a.display_name.localeCompare(b.display_name);
                      })
                      .map((part) => {
                        const partBooks: EnsemblePartBook[] = (ensemble.part_books ?? [])
                          .filter((b) => b.part_display_name === part.display_name)
                          .sort((a, b) => b.revision - a.revision);
                        const latestBook = partBooks[0];
                        const olderBooks = partBooks.slice(1);
                        const latestRev = ensemble.latest_part_book_revision ?? 0;
                        const isExpanded = expandedPartId === part.id;

                        return (
                          <div key={part.id}>
                            <Card withBorder radius="sm" p="sm" mb="xs">
                              <Group justify="space-between" wrap="nowrap">
                                <Group gap="xs" style={{ minWidth: 0 }}>
                                  <ActionIcon
                                    variant="subtle"
                                    size="sm"
                                    onClick={() => setExpandedPartId(isExpanded ? null : part.id)}
                                    disabled={olderBooks.length === 0}
                                    title={olderBooks.length ? 'Older revisions' : undefined}
                                  >
                                    {olderBooks.length > 0 ? (
                                      isExpanded ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />
                                    ) : (
                                      <IconChevronRight size={16} style={{ opacity: 0.3 }} />
                                    )}
                                  </ActionIcon>
                                  <Text size="sm" fw={600}>{part.display_name}</Text>
                                  {latestBook && (
                                    <>
                                      <Badge size="xs" variant="light" color={latestBook.revision === latestRev ? 'teal' : 'gray'}>
                                        r{latestBook.revision} {latestBook.revision === latestRev ? '(latest)' : ''}
                                      </Badge>
                                      {!latestBook.is_rendered && (
                                        <Badge size="xs" variant="light" color="yellow">Rendering…</Badge>
                                      )}
                                    </>
                                  )}
                                  {!latestBook && (
                                    <Text size="xs" c="dimmed">No part book</Text>
                                  )}
                                </Group>
                                <Group>
                                  {(part.arrangements) && (length <= 2)  && (
                                    <>
                                      {part.arrangements.map((arr) => ( 
                                        <Text size="xs" c="dimmed">{arr} </Text>
                                      ))}
                                    </>
                                  )}
                                  {(part.arrangements) && (length >2) && (
                                    <>
                                      <Text size="xs" c="dimmed">{part.arrangements[0]}</Text>
                                      <Text size="xs" c="dimmed">... {part.arrangements.length - 1} more</Text>
                                    {part.arrangements.map((arr) => ( <Text size="xs" c="dimmed">{arr}</Text> ))}
                                    </>
                                  )}
                                </Group>
                                {latestBook?.is_rendered && latestBook.download_url && (
                                  <Button
                                    component="a"
                                    href={latestBook.download_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconDownload size={14} />}
                                  >
                                    Download
                                  </Button>
                                )}
                              </Group>
                              <Collapse in={isExpanded && olderBooks.length > 0}>
                                <Stack gap="xs" mt="sm" pl="md" style={{ borderLeft: '2px solid var(--mantine-color-default-border)' }}>
                                  <Text size="xs" c="dimmed" fw={500}>Older revisions</Text>
                                  {olderBooks.map((book) => (
                                    <Group key={book.id} justify="space-between">
                                      <Group gap="xs">
                                        <Text size="sm">Revision {book.revision}</Text>
                                        {!book.is_rendered && (
                                          <Badge size="xs" variant="light" color="yellow">Rendering…</Badge>
                                        )}
                                      </Group>
                                      {book.is_rendered && book.download_url && (
                                        <Button
                                          component="a"
                                          href={book.download_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          size="xs"
                                          variant="subtle"
                                          leftSection={<IconDownload size={12} />}
                                        >
                                          Download
                                        </Button>
                                      )}
                                    </Group>
                                  ))}
                                </Stack>
                              </Collapse>
                            </Card>
                          </div>
                        );
                      })}
                  </Stack>
                )}
              </div>
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};

export default ArrangementsPage;