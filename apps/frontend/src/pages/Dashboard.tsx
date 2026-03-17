import { Title, Text, Container } from '@mantine/core';

export default function Dashboard() {
  return (
    <Container>
      <Title>Dashboard</Title>
      <Text>This is a protected area for logged-in users.</Text>
    </Container>
  );
}
