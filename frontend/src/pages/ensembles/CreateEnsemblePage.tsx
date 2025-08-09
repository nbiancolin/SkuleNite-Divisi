import { useState } from "react";
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  TextInput,
  SegmentedControl,
} from "@mantine/core";
import { X, } from "lucide-react";
import { apiService } from '../../services/apiService';


export default function CreateEnsemblePage() {
  const [error, setError] = useState<string | null>(null);
  const [ensembleName, setEnsebleName] = useState<string>("My First Ensemble")
  const [selectedStyle, setSelectedStyle] = useState<string>("broadway")

  const createEnsemble = async () => {

    try {
      const data = await apiService.createEnsemble(ensembleName, selectedStyle)
      
      window.location.href = `/app/ensembles/${data.slug}/arrangements`;
      //once finished, redirect to that ensebles page (for testing, use all ensembles page
    } catch (err: any) {
      console.error("Formatting error:", err);
      setError(err.response?.data?.detail || "Formatting failed.");  //TODO[SC-XX] make this acc display the error at hand
    } 
  };

  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        Get started with Divisi
      </Title>
      <Text>Enter the name of your ensemble.</Text>
      <Text>Note that ensemble names are unique.</Text>
      <TextInput
        label="Ensemble Name"
        value={ensembleName}
        onChange={(e) => setEnsebleName(e.currentTarget.value)}
        mt="md"
      />

      <Text mt="md"> Default Style for Arrangements in this ensemble:</Text>

      <SegmentedControl 
              fullWidth
              size="md"
              mt="md"
              value={selectedStyle}
              onChange={setSelectedStyle}
              data={[
                {label: "Broadway", value: "broadway"},
                {label: "Jazz", value: "jazz"},
                {label: "Classical", value: "classical"},
              ]}
            />

      <Button
        onClick={createEnsemble}
        fullWidth
        mt="md"
      >
        Create Ensemble
      </Button>

      {error && (
        <Notification
          mt="xl"
          icon={<X size={18} />}
          color="red"
          title="Error"
          onClose={() => setError(null)}
        >
          {error}
        </Notification>
      )}
    </Container>
  );
}
