import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, Container, Title, Loader, Center } from '@mantine/core';
import { useLocation } from 'react-router-dom';

interface Ensemble {
  id: number;
  name: string;
  arrangements: number[];
}

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

const EnsemblesPage: React.FC = () => {
  const [ensembles, setEnsembles] = useState<EnsembleWithArrangements[]>([]);
  const [ensemblesWithArrangements, setEnsemblesWithArrangements] = useState<EnsembleWithArrangements[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const query = useQuery();
  const id = query.get('id');

  useEffect(() => {
    const fetchEnsembles = async () => {
      try {
        let response;
        if (id) {
          response = await axios.get<EnsembleWithArrangements[]>(`http://localhost:8000/api/ensembles/?id=${id}`);
          setEnsembles(response.data);
        } else {
          response = await axios.get<EnsembleWithArrangements[]>("http://localhost:8000/api/ensembles/");
          
        }
        console.log(response)
        setEnsemblesWithArrangements(response.data)
        
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

  if (id) {
    const rows = ensemblesWithArrangements.flatMap((ensemble) =>
      ensemble.arrangements.map((arrangement) => (
        <Table.Tr key={arrangement.id}>
          <Table.Td>{ensemble.name}</Table.Td>
          <Table.Td>{arrangement.title}</Table.Td>
          <Table.Td>{arrangement.subtitle}</Table.Td>
          <Table.Td>{arrangement.mvt_no}</Table.Td>
        </Table.Tr>
      ))
    );
    return (
      <Container py="md">
        <Title order={2} mb="md">Arrangements for Ensemble</Title>
        <Table striped highlightOnHover withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Ensemble Name</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Subtitle</Table.Th>
              <Table.Th>Movement No</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>{rows}</Table.Tbody>
        </Table>
      </Container>
    );
  } else {
    console.log(ensembles)
    const rows = ensembles.map((ensemble) => (
      <Table.Tr key={ensemble.id}>
        <Table.Td>{ensemble.id}</Table.Td>
        <Table.Td>
          <a href={`/testing/ensembles?id=${ensemble.id}`}>{ensemble.name}</a>
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
  }


  
};

export default EnsemblesPage;