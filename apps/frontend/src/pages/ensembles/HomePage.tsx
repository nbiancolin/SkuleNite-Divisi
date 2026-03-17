import { Link } from 'react-router-dom';
import { Stack, Title, Text, Button } from '@mantine/core';
import { IconHome, IconMusic } from '@tabler/icons-react';

const HomePage = () => {
  return (
    <Stack gap="lg" align="center" py="xl">
      <IconHome size={64} color="var(--mantine-color-blue-6)" />
      <Title order={1}>Music Arrangement Manager</Title>
      <Text size="lg" c="dimmed" ta="center">
        Organize and manage your musical ensembles and arrangements
      </Text>
      <Button
        component={Link}
        to="/app/ensembles"
        size="lg"
        rightSection={<IconMusic size={20} />}
      >
        View Ensembles
      </Button>
    </Stack>
  );
};

export default HomePage;