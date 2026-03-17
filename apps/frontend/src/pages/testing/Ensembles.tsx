import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, Container, Title, Loader, Center } from '@mantine/core';

interface Arrangements {
  id: number;
  ensemble_name: string;
  title: string;
  subtitle: string;
  mvt_no: string;
}

interface EnsembleWithArrangements {
  id: number;
  name: string;
  arrangements: Arrangements[]
}

const API_BASE_URL = import.meta.env.VITE_API_URL;

const EnsemblesPage: React.FC = () => {
  const [ensembles, setEnsembles] = useState<EnsembleWithArrangements[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchEnsembles = async () => {
      try {
        let response;
        response = await axios.get<EnsembleWithArrangements[]>(`${API_BASE_URL}/ensembles/`);
        setEnsembles(response.data);
        
      } catch (error) {
        console.error('Failed to fetch ensembles:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEnsembles();
  });

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
      <Table.Td>
        <a href={`/testing/arrangements?ensemble_id=${ensemble.id}`}>{ensemble.name}</a>
      </Table.Td>
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