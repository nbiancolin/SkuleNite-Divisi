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
  Modal,
  Avatar,
  Select,
  Tabs,
} from '@mantine/core';
import { 
  IconAlertCircle, 
  IconTrash,
  IconBook,
  IconDownload,
  IconRefresh,
  IconChevronDown,
  IconChevronRight,
  IconGripVertical,
} from '@tabler/icons-react';
import { apiService } from '../../services/apiService';
import { useParams, Link } from 'react-router-dom';

import type { Ensemble, PartName, EnsemblePartBook } from '../../services/apiService';

export default function EnsembleDisplay() {
  const { slug = '' } = useParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ensemble, setEnsemble] = useState<Ensemble | null>(null);

  const [editing, setEditing] = useState(false);
  const [nameDraft, setNameDraft] = useState('');
  const [joinLinkDraft, setJoinLinkDraft] = useState<string | null | undefined>('');
  const [saving, setSaving] = useState(false);

  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false);
  const [removeCandidate, setRemoveCandidate] = useState<{ id: number; username: string } | null>(null);

  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [mergeFirstId, setMergeFirstId] = useState<string | null>(null);
  const [mergeSecondId, setMergeSecondId] = useState<string | null>(null);
  const [mergeNewDisplayName, setMergeNewDisplayName] = useState<string>('');
  const [expandedPartId, setExpandedPartId] = useState<number | null>(null);
  const [reorderingParts, setReorderingParts] = useState(false);
  const [draggedPartId, setDraggedPartId] = useState<number | null>(null);
  const [dragOverPartId, setDragOverPartId] = useState<number | null>(null);

  // helper to read CSRF token from cookies (same logic as apiService)
  function getCsrfToken(): string | null {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const fetchEnsemble = async (slug: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getEnsemble(slug);
      setEnsemble(data);
      // seed drafts
      setNameDraft(data?.name || '');
      setJoinLinkDraft(data?.join_link || '');
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (slug) fetchEnsemble(slug);
  }, [slug]);

  // Poll ensemble while part books are generating
  useEffect(() => {
    if (!slug || !ensemble?.part_books_generating) return;
    const interval = setInterval(() => fetchEnsemble(slug), 3000);
    return () => clearInterval(interval);
  }, [slug, ensemble?.part_books_generating]);

  const handleRemoveUserClick = (userId: number, username: string) => {
    setRemoveCandidate({ id: userId, username });
    setConfirmRemoveOpen(true);
  };

  const confirmRemove = async () => {
    if (!removeCandidate || !ensemble) return;
    try {
      setSaving(true);
      await apiService.removeUserFromEnsemble(removeCandidate.id, ensemble.slug);
      // refresh
      await fetchEnsemble(ensemble.slug);
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setSaving(false);
      setConfirmRemoveOpen(false);
      setRemoveCandidate(null);
    }
  };

  const handleRoleChange = async (userId: number, newRole: 'M' | 'A') => {
    if (!ensemble) return;
    try {
      setSaving(true);
      await apiService.changeUserRole(userId, ensemble.slug, newRole);
      // refresh
      await fetchEnsemble(ensemble.slug);
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setSaving(false);
    }
  };

  const cancelRemove = () => {
    setConfirmRemoveOpen(false);
    setRemoveCandidate(null);
  };

  const handleSaveEnsemble = async () => {
    if (!ensemble) return;
    try {
      setSaving(true);
      setError(null);
      const url = `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/ensembles/${ensemble.slug}/`;
      const csrf = getCsrfToken();
      const headers: Record<string, string> = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      };
      if (csrf) headers['X-CSRFToken'] = csrf;

      const body = JSON.stringify({
        name: nameDraft,
        join_link: joinLinkDraft,
      });

      const resp = await fetch(url, {
        method: 'PUT',
        headers,
        credentials: 'include',
        body,
      });

      if (!resp.ok) {
        let errText = '';
        try {
          const errJson = await resp.json();
          errText = errJson.detail || JSON.stringify(errJson);
        } catch {
          errText = await resp.text();
        }
        throw new Error(`Failed to update ensemble (status ${resp.status}) - ${errText}`);
      }

      // refresh from server
      await fetchEnsemble(ensemble.slug);
      setEditing(false);
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container size="md" py="xl">
        <Paper shadow="sm" p="xl" radius="md">
          <Group justify="center">
            <Loader size="xl" />
            <Text size="lg">Loading ensemble...</Text>
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
        </Alert>
      </Container>
    );
  }

  if (!ensemble) {
    return (
      <Container size="md" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} title="Not Found" color="orange">
          Ensemble not found.
        </Alert>
      </Container>
    );
  }

  const isAdmin = !!ensemble.is_admin;

  const partNames: PartName[] = (() => {
    // Prefer backend shape (`part_names`), fallback to older (`part_name`)
    const raw = (ensemble as any).part_names ?? (ensemble as any).part_name ?? [];
    if (!Array.isArray(raw)) return [];

    return raw
      .map((p: any) => {
        if (p && typeof p === 'object') {
          // New backend shape
          if (typeof p.id === 'number' && typeof p.display_name === 'string') {
            return { id: p.id, display_name: p.display_name, arrangements: p.arrangements } as PartName;
          }
          // Old backend shape: { [id]: "name" }
          const entries = Object.entries(p);
          if (entries.length === 1) {
            const [idStr, name] = entries[0];
            const id = Number(idStr);
            if (Number.isFinite(id) && typeof name === 'string') {
              return { id, display_name: name } as PartName;
            }
          }
        }
        return null;
      })
      .filter(Boolean) as PartName[];
  })();

  const partNameSelectData = partNames
    .slice()
    .sort((a, b) => a.display_name.localeCompare(b.display_name))
    .map((p) => ({ value: String(p.id), label: p.display_name }));

  const handleGeneratePartBooks = async () => {
    if (!ensemble) return;
    try {
      setError(null);
      await apiService.generatePartBooksForEnsemble(ensemble.slug);
      await fetchEnsemble(ensemble.slug);
    } catch (err: any) {
      setError(err?.message || String(err));
    }
  };

  const handleMergePartNames = async () => {
    if (!ensemble) return;
    const firstId = Number(mergeFirstId);
    const secondId = Number(mergeSecondId);
    if (!Number.isFinite(firstId) || !Number.isFinite(secondId) || firstId === secondId) {
      setError('Please select two different part names to merge.');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await apiService.mergePartNames(
        ensemble.slug,
        firstId,
        secondId,
        mergeNewDisplayName.trim() ? mergeNewDisplayName.trim() : null
      );
      await fetchEnsemble(ensemble.slug);
      setMergeModalOpen(false);
      setMergeFirstId(null);
      setMergeSecondId(null);
      setMergeNewDisplayName('');
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Container size="md" py="xl">
      <Paper shadow="sm" p="xl" radius="md">
        <Group align="center" mb="md">
          <Group align="center">
            <Title order={2}>{ensemble.name}</Title>
            <Badge color="gray" variant="outline">{ensemble.slug}</Badge>
            {ensemble.is_admin && <Badge color="teal">Owner</Badge>}
          </Group>
          <Group>
            <Button component={Link} to="/app/ensembles" variant="subtle">Back</Button>
            {isAdmin && (
              <Button onClick={() => setEditing((s) => !s)}>
                {editing ? 'Cancel' : 'Edit'}
              </Button>
            )}
          </Group>
        </Group>

        <Collapse in={editing}>
          <Card withBorder mb="md">
            <Stack>
              <TextInput label="Ensemble name" value={nameDraft} onChange={(e) => setNameDraft(e.currentTarget.value)} />
              <TextInput label="Join link (preview)" value={joinLinkDraft ?? ''} onChange={(e) => setJoinLinkDraft(e.currentTarget.value)} />
              <Group>
                <Button onClick={handleSaveEnsemble} loading={saving}>Save</Button>
                <Button variant="outline" onClick={() => { setEditing(false); setNameDraft(ensemble.name); setJoinLinkDraft(ensemble.join_link); }}>Cancel</Button>
              </Group>
            </Stack>
          </Card>
        </Collapse>

        <Tabs defaultValue="overview" mt="md">
          <Tabs.List>
            <Tabs.Tab value="overview">Overview</Tabs.Tab>
            <Tabs.Tab value="parts">Parts & part books</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="overview" pt="md">
            <Grid>
              <Grid.Col span={6}>
                <Card withBorder mb="md">
                  <Group mb="xs" justify="space-between">
                    <Group>
                      <Text fw={500}>Arrangements</Text>
                      <Badge size="sm" variant="light">{ensemble.arrangements?.length ?? 0}</Badge>
                    </Group>
                    <Button component={Link} to={`/app/ensembles/${ensemble.slug}/arrangements`} size="xs" variant="subtle">
                      View all
                    </Button>
                  </Group>
                  <Divider />
                  <div style={{ height: 320, overflowY: 'auto', minHeight: 0 }}>
                    <Stack mt="md" gap="xs">
                      {(ensemble.arrangements && ensemble.arrangements.length > 0) ? (
                        ensemble.arrangements.slice(0, 8).map((arr: any) => (
                          <Card key={arr.id} withBorder radius="sm" p="sm" component={Link} to={`/app/arrangements/${arr.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                            <Text size="sm" fw={500} lineClamp={1}>{arr.title}{arr.subtitle ? ` — ${arr.subtitle}` : ''}</Text>
                            <Text size="xs" c="dimmed">{arr.composer ?? ''} {arr.mvt_no ? `· Mvt ${arr.mvt_no}` : ''}</Text>
                          </Card>
                        ))
                      ) : (
                        <Text size="sm" c="dimmed">No arrangements yet.</Text>
                      )}
                      {ensemble.arrangements && ensemble.arrangements.length > 8 && (
                        <Button component={Link} to={`/app/ensembles/${ensemble.slug}/arrangements`} variant="light" size="xs" fullWidth>
                          +{ensemble.arrangements.length - 8} more
                        </Button>
                      )}
                    </Stack>
                  </div>
                </Card>
              </Grid.Col>

              <Grid.Col span={6}>
                <Card withBorder mb="md">
                  <Group mb="xs">
                    <Text fw={500}>Members</Text>
                    <Badge size="sm" variant="light">{ensemble.userships?.length ?? 0}</Badge>
                  </Group>
                  <Divider />
                  <div style={{ maxHeight: 260, overflowY: 'auto' }}>
                    <Table verticalSpacing="sm" miw={260}>
                      <tbody>
                        {(ensemble.userships && ensemble.userships.length > 0) ? ensemble.userships.map((ship) => (
                          <tr key={ship.user.id}>
                            <td style={{ width: 36 }}>
                              <Avatar size={28} radius="xl">{(ship.user.username || 'U').charAt(0).toUpperCase()}</Avatar>
                            </td>
                            <td>
                              <Text size="sm">{ship.user.username}</Text>
                              <Text size="xs" c="dimmed" lineClamp={1}>{ship.user.email}</Text>
                            </td>
                            <td>
                              <Badge size="xs" color={ship.role === 'A' ? 'teal' : 'gray'} variant="light">
                                {ship.role === 'A' ? 'Admin' : 'Member'}
                              </Badge>
                            </td>
                            <td style={{ textAlign: 'right', width: 80 }}>
                              {isAdmin && (
                                <Group gap={4} justify="flex-end">
                                  <Select
                                    value={ship.role}
                                    onChange={(value) => value && handleRoleChange(ship.user.id, value as 'M' | 'A')}
                                    data={[
                                      { value: 'M', label: 'Member' },
                                      { value: 'A', label: 'Admin' },
                                    ]}
                                    size="xs"
                                    w={82}
                                    disabled={saving}
                                  />
                                  <Tooltip label="Remove user" position="left" withArrow>
                                    <ActionIcon color="red" size="sm" onClick={() => handleRemoveUserClick(ship.user.id, ship.user.username)}>
                                      <IconTrash size={14} />
                                    </ActionIcon>
                                  </Tooltip>
                                </Group>
                              )}
                            </td>
                          </tr>
                        )) : (
                          <tr><td colSpan={4}><Text size="sm" c="dimmed">No members</Text></td></tr>
                        )}
                      </tbody>
                    </Table>
                  </div>
                </Card>

                <Card withBorder>
                  <Text size="xs" c="dimmed" mb={4}>Invite link</Text>
                  <Group gap="xs">
                    <Text size="sm" style={{ flex: 1, minWidth: 0 }} truncate>{ensemble.join_link ?? 'No invite link'}</Text>
                    {isAdmin && (
                      <Button size="xs" variant="outline" onClick={async () => {
                        try {
                          const data = await apiService.getInviteLink(ensemble.slug);
                          await fetchEnsemble(ensemble.slug);
                          setJoinLinkDraft(data?.invite_link ?? data?.join_link ?? ensemble.join_link);
                        } catch (err: any) {
                          setError(err?.message || String(err));
                        }
                      }}>Generate</Button>
                    )}
                  </Group>
                </Card>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          <Tabs.Panel value="parts" pt="md">
            <Card withBorder>
              <Group mb="xs" justify="space-between">
                <Group gap="xs">
                  <IconBook size={18} />
                  <Text fw={500}>Parts & part books</Text>
                  <Badge size="sm" variant="light">{partNames.length} parts</Badge>
                  {ensemble.part_books_generating && (
                    <Badge color="blue" variant="light" leftSection={<Loader size={12} />}>
                      Generating…
                    </Badge>
                  )}
                </Group>
                {isAdmin && (
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => setMergeModalOpen(true)}
                      disabled={partNames.length < 2}
                    >
                      Merge part names
                    </Button>
                    <Button
                      size="sm"
                      variant="filled"
                      leftSection={<IconRefresh size={14} />}
                      onClick={handleGeneratePartBooks}
                      disabled={!!ensemble.part_books_generating || partNames.length === 0}
                    >
                      Generate part books
                    </Button>
                  </Group>
                )}
              </Group>
              <Divider />
              <div style={{ maxHeight: 480, overflowY: 'auto' }}>
                {partNames.length === 0 ? (
                  <Text mt="md" size="sm" c="dimmed">
                    No part names yet. Part names are added when you upload arrangement versions with parts.
                  </Text>
                ) : (
                  <Stack mt="md" gap={0}>
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
                      .map((part, index, sortedParts) => {
                        const partBooks: EnsemblePartBook[] = (ensemble.part_books ?? [])
                          .filter((b) => b.part_display_name === part.display_name)
                          .sort((a, b) => b.revision - a.revision);
                        const latestBook = partBooks[0];
                        const olderBooks = partBooks.slice(1);
                        const latestRev = ensemble.latest_part_book_revision ?? 0;
                        const isExpanded = expandedPartId === part.id;

                        const isDragging = draggedPartId === part.id;
                        const isDragOver = dragOverPartId === part.id;

                        const handleDragStart = (e: React.DragEvent) => {
                          if (!ensemble?.is_admin) return;
                          setDraggedPartId(part.id);
                          e.dataTransfer.effectAllowed = 'move';
                          e.dataTransfer.setData('text/plain', part.id.toString());
                          // Make the dragged element semi-transparent
                          if (e.currentTarget instanceof HTMLElement) {
                            e.currentTarget.style.opacity = '0.5';
                          }
                        };

                        const handleDragEnd = (e: React.DragEvent) => {
                          setDraggedPartId(null);
                          setDragOverPartId(null);
                          // Reset opacity
                          if (e.currentTarget instanceof HTMLElement) {
                            e.currentTarget.style.opacity = '1';
                          }
                        };

                        const handleDragOver = (e: React.DragEvent) => {
                          if (!ensemble?.is_admin || draggedPartId === part.id) return;
                          e.preventDefault();
                          e.dataTransfer.dropEffect = 'move';
                          setDragOverPartId(part.id);
                        };

                        const handleDragLeave = () => {
                          setDragOverPartId(null);
                        };

                        const handleDrop = async (e: React.DragEvent) => {
                          e.preventDefault();
                          if (!ensemble?.is_admin || draggedPartId === null || draggedPartId === part.id) {
                            setDragOverPartId(null);
                            return;
                          }

                          const draggedIndex = sortedParts.findIndex(p => p.id === draggedPartId);
                          const targetIndex = index;

                          if (draggedIndex === -1 || draggedIndex === targetIndex) {
                            setDragOverPartId(null);
                            return;
                          }

                          // Create new order array
                          const reorderedParts = [...sortedParts];
                          const [draggedPart] = reorderedParts.splice(draggedIndex, 1);
                          reorderedParts.splice(targetIndex, 0, draggedPart);

                          // Update orders based on new positions
                          const updatedParts = reorderedParts.map((p, i) => ({
                            ...p,
                            order: i
                          }));

                          try {
                            setReorderingParts(true);
                            await apiService.updatePartOrder(
                              slug,
                              updatedParts.map(p => ({ id: p.id, order: p.order ?? 0 }))
                            );
                            // Refresh ensemble data
                            const updated = await apiService.getEnsemble(slug);
                            setEnsemble(updated);
                          } catch (err) {
                            console.error('Failed to update part order:', err);
                            alert('Failed to update part order. Please try again.');
                          } finally {
                            setReorderingParts(false);
                            setDragOverPartId(null);
                            setDraggedPartId(null);
                          }
                        };

                        return (
                          <div key={part.id}>
                            <Card 
                              withBorder 
                              radius="sm" 
                              p="sm" 
                              mb="xs"
                              draggable={ensemble?.is_admin && !reorderingParts}
                              onDragStart={handleDragStart}
                              onDragEnd={handleDragEnd}
                              onDragOver={handleDragOver}
                              onDragLeave={handleDragLeave}
                              onDrop={handleDrop}
                              style={{
                                cursor: ensemble?.is_admin ? (isDragging ? 'grabbing' : 'grab') : 'default',
                                opacity: isDragging ? 0.5 : 1,
                                borderColor: isDragOver ? 'var(--mantine-color-blue-6)' : undefined,
                                borderWidth: isDragOver ? 2 : undefined,
                                backgroundColor: isDragOver ? 'var(--mantine-color-blue-0)' : undefined,
                                transition: 'background-color 0.2s, border-color 0.2s',
                              }}
                            >
                              <Group justify="space-between" wrap="nowrap">
                                <Group gap="xs" style={{ minWidth: 0 }}>
                                  {ensemble?.is_admin && (
                                    <ActionIcon
                                      variant="subtle"
                                      size="sm"
                                      style={{ cursor: 'grab' }}
                                      title="Drag to reorder"
                                      onMouseDown={(e) => e.stopPropagation()}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <IconGripVertical size={16} />
                                    </ActionIcon>
                                  )}
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
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Paper>

      <Modal opened={confirmRemoveOpen} onClose={cancelRemove} title="Confirm remove user">
        <Text>Remove {removeCandidate?.username}? This action will remove them from the ensemble.</Text>
        <Group mt="md">
          <Button variant="outline" onClick={cancelRemove}>Cancel</Button>
          <Button color="red" onClick={confirmRemove} loading={saving}>Remove</Button>
        </Group>
      </Modal>

      <Modal
        opened={mergeModalOpen}
        onClose={() => setMergeModalOpen(false)}
        title="Merge part names"
      >
        <Stack>
          <Select
            label="Keep"
            placeholder="Choose the part name to keep"
            data={partNameSelectData}
            value={mergeFirstId}
            onChange={setMergeFirstId}
            searchable
          />
          <Select
            label="Merge into it"
            placeholder="Choose the part name to merge"
            data={partNameSelectData}
            value={mergeSecondId}
            onChange={setMergeSecondId}
            searchable
          />
          <TextInput
            label="New display name (optional)"
            placeholder="Leave blank to keep the chosen name"
            value={mergeNewDisplayName}
            onChange={(e) => setMergeNewDisplayName(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="outline" onClick={() => setMergeModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleMergePartNames}
              loading={saving}
              disabled={!mergeFirstId || !mergeSecondId}
            >
              Merge
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
