import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Title,
  Card,
  Text,
  Button,
  Group,
  Stack,
  Loader,
  Alert,
} from '@mantine/core';
import { IconCheck, IconX, IconMusic } from '@tabler/icons-react';
import { apiService } from '../../services/apiService';

const JoinEnsemblePage = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ensembleInfo, setEnsembleInfo] = useState<{
    ensemble: {
      id: number;
      name: string;
      slug: string;
    };
    is_authenticated: boolean;
    already_member: boolean;
  } | null>(null);
  const [joinSuccess, setJoinSuccess] = useState(false);

  useEffect(() => {
    const fetchEnsembleInfo = async () => {
      if (!token) {
        setError('Invalid invite link');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const data = await apiService.getEnsembleByToken(token);
        setEnsembleInfo(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to load ensemble information');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchEnsembleInfo();
  }, [token]);

  const handleLogin = () => {
    // Redirect to login with the join URL as the next parameter
    const currentUrl = window.location.href;
    apiService.handleLogin(currentUrl)
  };

  const handleJoin = async () => {
    if (!token) return;

    try {
      setJoining(true);
      setError(null);
      const result = await apiService.joinEnsemble(token);
      setJoinSuccess(true);
      // Redirect to the ensemble after a short delay
      setTimeout(() => {
        if (result.ensemble?.slug) {
          navigate(`/app/ensembles/${result.ensemble.slug}/arrangements`);
        } else {
          navigate('/app/ensembles');
        }
      }, 2000);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to join ensemble');
      }
    } finally {
      setJoining(false);
    }
  };

  if (loading) {
    return (
      <Container size="sm" py="xl">
        <Stack align="center" gap="md">
          <Loader size="lg" />
          <Text>Loading ensemble information...</Text>
        </Stack>
      </Container>
    );
  }

  if (error && !ensembleInfo) {
    return (
      <Container size="sm" py="xl">
        <Alert color="red" title="Error" icon={<IconX />}>
          {error}
        </Alert>
      </Container>
    );
  }

  if (!ensembleInfo) {
    return (
      <Container size="sm" py="xl">
        <Alert color="yellow" title="Invalid Link">
          The invite link is invalid or has expired.
        </Alert>
      </Container>
    );
  }

  if (joinSuccess) {
    return (
      <Container size="sm" py="xl">
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack align="center" gap="md">
            <IconCheck size={48} color="var(--mantine-color-green-6)" />
            <Title order={2}>Successfully Joined!</Title>
            <Text>You've been added to {ensembleInfo.ensemble.name}.</Text>
            <Text size="sm" c="dimmed">Redirecting...</Text>
          </Stack>
        </Card>
      </Container>
    );
  }

  return (
    <Container size="sm" py="xl">
      <Card shadow="sm" padding="xl" radius="md" withBorder>
        <Stack gap="lg">
          <Group justify="center">
            <IconMusic size={48} color="var(--mantine-color-blue-6)" />
          </Group>
          
          <Stack align="center" gap="xs">
            <Title order={2}>Join Ensemble</Title>
            <Text size="xl" fw={500}>
              {ensembleInfo.ensemble.name}
            </Text>
          </Stack>

          {error && (
            <Alert color="red" title="Error" icon={<IconX />}>
              {error}
            </Alert>
          )}

          {ensembleInfo.already_member ? (
            <Alert color="blue" title="Already a Member">
              You are already a member of this ensemble.
            </Alert>
          ) : !ensembleInfo.is_authenticated ? (
            <Stack gap="md">
              <Text ta="center" c="dimmed">
                Please log in to join this ensemble.
              </Text>
              <Button
                fullWidth
                size="lg"
                onClick={handleLogin}
              >
                Log in with Discord
              </Button>
            </Stack>
          ) : (
            <Stack gap="md">
              <Text ta="center" c="dimmed">
                Click the button below to join this ensemble.
              </Text>
              <Button
                fullWidth
                size="lg"
                onClick={handleJoin}
                loading={joining}
              >
                Join Ensemble
              </Button>
            </Stack>
          )}
        </Stack>
      </Card>
    </Container>
  );
};

export default JoinEnsemblePage;

