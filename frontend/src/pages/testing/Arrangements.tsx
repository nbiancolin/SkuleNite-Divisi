import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, Container, Title, Loader, Center } from '@mantine/core';
import { useLocation, useNavigate } from 'react-router-dom';

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

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

const ArrangementsPage: React.FC = () => {
  const [ensemblesWithArrangements, setEnsemblesWithArrangements] = useState<EnsembleWithArrangements[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const query = useQuery();
  const id = query.get('ensemble_id');
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) {
      navigate('/testing/ensembles');
    }
  }, [id, navigate]);

  useEffect(() => {
    const fetchEnsembles = async () => {
      if (!id) return; // skip if no id

      try {
        const response = await axios.get<EnsembleWithArrangements[]>(`http://localhost:8000/api/ensembles/?id=${id}`);
        setEnsemblesWithArrangements(response.data);
      } catch (error) {
        console.error('Failed to fetch ensembles:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEnsembles();
  }, [id]);

  if (loading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    );
  }

  const rows = ensemblesWithArrangements.flatMap((ensemble) =>
    ensemble.arrangements.map((arrangement) => (
      <Table.Tr key={arrangement.id}>
        <Table.Td>{arrangement.mvt_no}</Table.Td>
        <Table.Td>{arrangement.title}</Table.Td>
        <Table.Td>{arrangement.subtitle}</Table.Td>
      </Table.Tr>
    ))
  );

  return (
    <Container py="md">
      <Title order={2} mb="md">
        Arrangements for Ensemble <em>{ensemblesWithArrangements[0].name}</em>
      </Title>
      <Table striped highlightOnHover withTableBorder withColumnBorders>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>#</Table.Th>
            <Table.Th>Title</Table.Th>
            <Table.Th>Subtitle</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>{rows}</Table.Tbody>
      </Table>
    </Container>
  );
};

export default ArrangementsPage;
