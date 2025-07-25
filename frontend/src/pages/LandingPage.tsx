import { Title, Text, Button, Container, Stack } from '@mantine/core';
import '@mantine/core/styles.css';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <Container>
      <Stack gap="lg" ta="center">
        <Title>Welcome to Divisi App!</Title>
        <Text>An Ensemble Score Management Site</Text>
        <Button component={Link} to="/part-formatter">
          Try our Part Formatter!
        </Button>
      </Stack>
    </Container>
  );
}
