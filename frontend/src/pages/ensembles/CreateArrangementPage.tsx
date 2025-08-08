import { useState } from "react";
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  TextInput,
} from "@mantine/core";
import { X, } from "lucide-react";
import { apiService } from '../../services/apiService';


export default function CeateArrangementPage() {
  const [error, setError] = useState<string | null>(null);
  const [ensembleSlug, setEnsembleSlug] = useState<string>("")
  const [title, setTitle] = useState<string>("")
  const [subtitle, setSubtitle] = useState<string>("")
  const [actNumber, setActNumber] = useState<number|null>(null)
  const [pieceNumber, setPieceNumber] = useState<number|null>(null)

  

  const createArrangment = async () => {

    try {
      const data = await apiService.createEnsemble(ensembleName)
      
      window.location.href = `/app/ensembles/${data.ensembleSlug}/arrangements`;
      //once finished, redirect to that ensebles page (for testing, use all ensembles page
    } catch (err: any) {
      console.error("Error when creating arrangement:", err);
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
        value={ensembleSlug}
        onChange={(e) => setEnsembleSlug(e.currentTarget.value)}
        mt="md"
        //TODO: This should not be editable -- just display it as a field of some kind
        // like, /app/ensembles/<slug>/create -- and get slug from that
      />

      <Button
        onClick={createEnsemble}
        fullWidth
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
