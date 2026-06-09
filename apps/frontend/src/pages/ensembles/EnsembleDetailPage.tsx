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
} from '@tabler/icons-react';
import { apiService } from '../../services/apiService';
import { useParams, Link } from 'react-router-dom';
import { usePageTitle } from '../../context/usePageTitle';

import type { Ensemble, PartName } from '../../services/apiService';
import { ScoreTitlePreview, type PreviewStyleName } from '../../components/ScoreTitlePreview';
import { PartNameMatrixEditor } from './PartNameMatrixEditor';
import { EnsemblePartBooksSection } from './EnsemblePartBooksSection';

type LegacyPartNameMap = Record<string, string>;
type EnsembleWithPartNames = Ensemble & {
  part_names?: unknown;
  part_name?: unknown;
};

export default function EnsembleDisplay() {
  const { slug = '' } = useParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ensemble, setEnsemble] = useState<Ensemble | null>(null);
  usePageTitle(ensemble?.name ?? null);

  const [editing, setEditing] = useState(false);
  const [nameDraft, setNameDraft] = useState('');
  const [selectedStyleDraft, setSelectedStyleDraft] = useState<PreviewStyleName>("broadway");

  const [saving, setSaving] = useState(false);

  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false);
  const [removeCandidate, setRemoveCandidate] = useState<{ id: number; username: string } | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>('overview');

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
      setNameDraft(data?.name || '');
      setSelectedStyleDraft(data.default_style);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
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
        default_style: selectedStyleDraft,
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
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
    const ensembleWithPartNames = ensemble as EnsembleWithPartNames;
    const raw = ensembleWithPartNames.part_names ?? ensembleWithPartNames.part_name ?? [];
    if (!Array.isArray(raw)) return [];

    return raw
      .map((p: unknown) => {
        if (p && typeof p === 'object') {
          // New backend shape
          if ('id' in p && 'display_name' in p && typeof p.id === 'number' && typeof p.display_name === 'string') {
            const arrangements = 'arrangements' in p && Array.isArray(p.arrangements)
              ? p.arrangements.filter((arr): arr is string => typeof arr === 'string')
              : undefined;
            return { id: p.id, display_name: p.display_name, arrangements } as PartName;
          }
          // Old backend shape: { [id]: "name" }
          const entries = Object.entries(p as LegacyPartNameMap);
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

  const isPartsTab = activeTab === 'parts';

  return (
    <Container fluid={isPartsTab} size={isPartsTab ? undefined : 'md'} py="xl">
      <Paper shadow="sm" p={isPartsTab ? 'lg' : 'xl'} radius="md">
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
                <ScoreTitlePreview
                  selectedStyle={selectedStyleDraft}
                  setSelectedStyle={setSelectedStyleDraft}
                  title={"Title"}
                  subtitle={"subtitle"}
                  ensemble={nameDraft}
                  composer={"composer"}
                  arranger={"arranger"}
                  mvtNo={"1"}
                />
              <Group>
                <Button onClick={handleSaveEnsemble} loading={saving}>Save</Button>
                <Button variant="outline" onClick={() => { setEditing(false); setNameDraft(ensemble.name); setSelectedStyleDraft(ensemble.default_style); }}>Cancel</Button>
              </Group>
            </Stack>
          </Card>
        </Collapse>

        <Tabs value={activeTab} onChange={setActiveTab} mt="md">
          <Tabs.List>
            <Tabs.Tab value="overview">Overview</Tabs.Tab>
            <Tabs.Tab value="parts">Parts</Tabs.Tab>
            <Tabs.Tab value="part-books">Part books</Tabs.Tab>
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
                        ensemble.arrangements.slice(0, 8).map((arr) => (
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
                  </Group>
                </Card>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          <Tabs.Panel value="parts" pt="md">
            <Group gap="xs" mb="md">
              <Text fw={600} size="lg">
                Part names
              </Text>
              <Badge size="sm" variant="light">
                {partNames.length} parts
              </Badge>
            </Group>
            <Text size="sm" c="dimmed" mb="md">
              Map and merge part names across arrangements. Drag a part onto a base column to link them for merging.
            </Text>
            <PartNameMatrixEditor
              ensembleSlug={slug}
              isAdmin={isAdmin}
              onSaved={() => fetchEnsemble(slug)}
            />
          </Tabs.Panel>

          <Tabs.Panel value="part-books" pt="md">
            <EnsemblePartBooksSection
              ensemble={ensemble}
              partNames={partNames}
              onRefresh={() => fetchEnsemble(slug)}
              onError={(message) => setError(message)}
            />
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

    </Container>
  );
}
