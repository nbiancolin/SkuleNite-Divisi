import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, Container, Title, Loader, Center } from '@mantine/core';
import { useSearchParams } from 'react-router-dom';

interface Arrangement {
  id: number;
  title: string;
  subtitle: string;
  arrangements: number[]
}

const ArrangementPage: React.FC = () => {
  const [arrangements, setArrangements] = useState<Arrangement[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  
  const [searchParams] = useSearchParams()
  const ensemble_id = searchParams.get("id")

  useEffect(() => {
    const fetchArrangements = async () => {
      try {
        const response = await axios.get<Arrangement[]>(`http://localhost:8000/api/arrangement/?ensemble=${ensemble_id}`);
        console.log(response)
        setArrangements(response.data);
      } catch (error) {
        console.error('Failed to fetch ensembles:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchArrangements();
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
      <Table.Td>
        <a href={`/ensembles?id=${ensemble.id}`}>{ensemble.title}</a>
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

export default ArrangementPage;
