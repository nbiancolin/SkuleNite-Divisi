import { Title, Text, Button, Container, Stack } from '@mantine/core';
import '@mantine/core/styles.css';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <Container>
      <Stack spacing="lg" align="center">
        <Title>Welcome to SkuleNite</Title>
        <Text>This is our awesome landing page!</Text>
        <Button component={Link} to="/dashboard">
          Go to Dashboard
        </Button>
      </Stack>
    </Container>
  );
}
