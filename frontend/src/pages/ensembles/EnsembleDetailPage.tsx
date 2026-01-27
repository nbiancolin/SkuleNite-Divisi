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
  Avatar,
  Select,
} from '@mantine/core';
import { 
  IconAlertCircle, 
  IconTrash,
} from '@tabler/icons-react';
import { apiService } from '../../services/apiService';
import { useParams, Link } from 'react-router-dom';

import type { Ensemble } from '../../services/apiService';

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

        <Grid>
          <Grid.Col span={6}>
            <Card withBorder mb="md">
              <Group mb="xs">
                <Text>Arrangements</Text>
                <Badge>{ensemble.arrangements?.length ?? 0}</Badge>
              </Group>
              <Divider />
              <ScrollArea style={{ maxHeight: 450 }}>
                <Stack mt="md">
                  {(ensemble.arrangements && ensemble.arrangements.length > 0) ? (
                    ensemble.arrangements.map((arr: any) => (
                      <Card key={arr.id} withBorder radius="sm" p="sm">
                        <Group>
                          <div>
                            <Text>{arr.title}{arr.subtitle ? ` — ${arr.subtitle}` : ''}</Text>
                            <Text size="sm" color="dimmed">{arr.composer ?? ''} {arr.mvt_no ? `· Mvt ${arr.mvt_no}` : ''}</Text>
                          </div>
                          <Group>
                            <Button component={Link} to={`/app/arrangements/${arr.id}`} size="xs" variant="outline">View</Button>
                          </Group>
                        </Group>
                      </Card>
                    ))
                  ) : (
                    <Text color="dimmed">No arrangements yet.</Text>
                  )}
                </Stack>
              </ScrollArea>
            </Card>
          </Grid.Col>

          <Grid.Col span={6}>
            <Card withBorder mb="md">
              <Group mb="xs">
                <Text>Members</Text>
                <Badge>{ensemble.userships?.length ?? 0}</Badge>
              </Group>
              <Divider />
              <ScrollArea style={{ maxHeight: 300 }}>
                <Table verticalSpacing="sm" miw={300}>
                  <tbody>
                    {(ensemble.userships && ensemble.userships.length > 0) ? ensemble.userships.map((ship) => (
                      <tr key={ship.user.id}>
                        <td style={{ width: 40 }}>
                          <Avatar size={28} radius="xl">{(ship.user.username || 'U').charAt(0).toUpperCase()}</Avatar>
                        </td>
                        <td>
                          <Text>{ship.user.username}</Text>
                          <Text size="xs" color="dimmed">{ship.user.email}</Text>
                        </td>
                        <td>
                          <Badge color={ship.role === 'A' ? 'teal' : 'gray'} variant="light">
                            {ship.role === 'A' ? 'Admin' : 'Member'}
                          </Badge>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <Group gap="xs">
                            {isAdmin && (
                              <Select
                                value={ship.role}
                                onChange={(value) => value && handleRoleChange(ship.user.id, value as 'M' | 'A')}
                                data={[
                                  { value: 'M', label: 'Member' },
                                  { value: 'A', label: 'Admin' },
                                ]}
                                size="xs"
                                w={100}
                                disabled={saving}
                              />
                            )}
                            {isAdmin && (
                              <Tooltip label="Remove user" position="left" withArrow>
                                <ActionIcon color="red" onClick={() => handleRemoveUserClick(ship.user.id, ship.user.username)}>
                                  <IconTrash size={16} />
                                </ActionIcon>
                              </Tooltip>
                            )}
                          </Group>
                        </td>
                      </tr>
                    )) : (
                      <tr><td colSpan={4}><Text color="dimmed">No members</Text></td></tr>
                    )}
                  </tbody>
                </Table>
              </ScrollArea>
            </Card>

            <Card withBorder>
              <Text size="sm" color="dimmed">Invite link</Text>
              <Group mt="xs">
                <Text size="sm" truncate>{ensemble.join_link ?? 'No invite link'}</Text>
                {isAdmin && (
                  <Button size="xs" variant="outline" onClick={async () => {
                    try {
                      const data = await apiService.getInviteLink(ensemble.slug);
                      // update local state and refetch
                      await fetchEnsemble(ensemble.slug);
                      setNameDraft((s) => s);
                      setJoinLinkDraft(data?.invite_link || data?.join_link || ensemble.join_link);
                    } catch (err: any) {
                      setError(err?.message || String(err));
                    }
                  }}>Generate</Button>
                )}
              </Group>
            </Card>
          </Grid.Col>
        </Grid>
        {/* TODO: HERE make some content to display part names and an action to merge them */}
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
