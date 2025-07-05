import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, Container, Title, Loader, Center } from '@mantine/core';

interface Ensemble {
  id: number;
  title: string;
  arrangements: number[]
}

const EnsemblesPage: React.FC = () => {
  const [ensembles, setEnsembles] = useState<Ensemble[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchEnsembles = async () => {
      try {
        const response = await axios.get<Ensemble[]>("http://localhost:8000/api/ensembles/");
        console.log(response)
        setEnsembles(response.data);
      } catch (error) {
        console.error('Failed to fetch ensembles:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEnsembles();
  }, []);

  if (loading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    );
  }

  const rows = ensembles.map((ensemble) => (
    <Table.Tr key={ensemble.id}>
      <Table.Td>{ensemble.id}</Table.Td>
      <Table.Td>{ensemble.title}</Table.Td>
    </Table.Tr>
  ));

  return (
    <Container py="md">
      <Title order={2} mb="md">Ensembles</Title>
      <Table striped highlightOnHover withTableBorder withColumnBorders>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>Name</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>{rows}</Table.Tbody>
      </Table>
    </Container>
  );
};

export default EnsemblesPage;
