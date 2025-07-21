import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import re
from collections import Counter
import pickle
import random
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import threading
import os

class CodeTokenizer:
    """Tokenizer for Python and C code"""
    
    def __init__(self):
        self.token_to_id = {}
        self.id_to_token = {}
        self.vocab_size = 0
        
    def build_vocab(self, code_pairs):
        """Build vocabulary from code pairs"""
        all_tokens = []
        
        for py_code, c_code in code_pairs:
            py_tokens = self.tokenize(py_code)
            c_tokens = self.tokenize(c_code)
            all_tokens.extend(py_tokens + c_tokens)
        
        # Add special tokens
        special_tokens = ['<PAD>', '<SOS>', '<EOS>', '<UNK>']
        token_counts = Counter(all_tokens)
        
        # Build vocabulary
        vocab = special_tokens + [token for token, count in token_counts.most_common(10000)]
        
        self.token_to_id = {token: i for i, token in enumerate(vocab)}
        self.id_to_token = {i: token for i, token in enumerate(vocab)}
        self.vocab_size = len(vocab)
        
    def tokenize(self, code):
        """Tokenize code into tokens"""
        tokens = re.findall(r'\w+|[^\w\s]', code)
        return tokens
    
    def encode(self, code):
        """Convert code to token IDs"""
        tokens = self.tokenize(code)
        return [self.token_to_id.get(token, self.token_to_id['<UNK>']) for token in tokens]
    
    def decode(self, token_ids):
        """Convert token IDs back to code"""
        tokens = [self.id_to_token.get(id, '<UNK>') for id in token_ids]
        return ' '.join(tokens)

class CodeDataset(Dataset):
    """Dataset for Python to C code translation"""
    
    def __init__(self, code_pairs, tokenizer, max_length=512):
        self.code_pairs = code_pairs
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self):
        return len(self.code_pairs)
    
    def __getitem__(self, idx):
        py_code, c_code = self.code_pairs[idx]
        
        # Encode sequences
        py_tokens = [self.tokenizer.token_to_id['<SOS>']] + self.tokenizer.encode(py_code) + [self.tokenizer.token_to_id['<EOS>']]
        c_tokens = [self.tokenizer.token_to_id['<SOS>']] + self.tokenizer.encode(c_code) + [self.tokenizer.token_to_id['<EOS>']]
        
        # Pad sequences
        py_tokens = self.pad_sequence(py_tokens, self.max_length)
        c_tokens = self.pad_sequence(c_tokens, self.max_length)
        
        return torch.tensor(py_tokens, dtype=torch.long), torch.tensor(c_tokens, dtype=torch.long)
    
    def pad_sequence(self, seq, max_length):
        """Pad sequence to max_length"""
        if len(seq) > max_length:
            return seq[:max_length]
        return seq + [self.tokenizer.token_to_id['<PAD>']] * (max_length - len(seq))

class AttentionMechanism(nn.Module):
    """Attention mechanism for sequence-to-sequence model"""
    
    def __init__(self, hidden_size):
        super(AttentionMechanism, self).__init__()
        self.hidden_size = hidden_size
        self.attention = nn.Linear(hidden_size * 2, hidden_size)
        self.v = nn.Linear(hidden_size, 1, bias=False)
        
    def forward(self, decoder_hidden, encoder_outputs):
        seq_len = encoder_outputs.size(1)
        decoder_hidden = decoder_hidden.unsqueeze(1).repeat(1, seq_len, 1)
        
        energy = torch.tanh(self.attention(torch.cat([decoder_hidden, encoder_outputs], dim=2)))
        attention_scores = self.v(energy).squeeze(2)
        
        attention_weights = torch.softmax(attention_scores, dim=1)
        context = torch.bmm(attention_weights.unsqueeze(1), encoder_outputs).squeeze(1)
        
        return context, attention_weights

class Encoder(nn.Module):
    """Encoder for Python code"""
    
    def __init__(self, vocab_size, embedding_dim, hidden_size, num_layers=2, dropout=0.1):
        super(Encoder, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(embedding_dim, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        embedded = self.dropout(self.embedding(x))
        outputs, (hidden, cell) = self.lstm(embedded)
        outputs = outputs[:, :, :self.hidden_size] + outputs[:, :, self.hidden_size:]
        return outputs, (hidden, cell)

class Decoder(nn.Module):
    """Decoder for C code generation"""
    
    def __init__(self, vocab_size, embedding_dim, hidden_size, num_layers=2, dropout=0.1):
        super(Decoder, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.vocab_size = vocab_size
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.attention = AttentionMechanism(hidden_size)
        self.lstm = nn.LSTM(embedding_dim + hidden_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        self.out = nn.Linear(hidden_size, vocab_size)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, hidden, cell, encoder_outputs):
        embedded = self.dropout(self.embedding(x))
        context, attention_weights = self.attention(hidden[-1], encoder_outputs)
        lstm_input = torch.cat([embedded, context.unsqueeze(1)], dim=2)
        output, (hidden, cell) = self.lstm(lstm_input, (hidden, cell))
        output = self.out(output)
        return output, hidden, cell, attention_weights

class Seq2SeqTranslator(nn.Module):
    """Complete sequence-to-sequence model for Python to C translation"""
    
    def __init__(self, vocab_size, embedding_dim=256, hidden_size=512, num_layers=2, dropout=0.1):
        super(Seq2SeqTranslator, self).__init__()
        
        self.encoder = Encoder(vocab_size, embedding_dim, hidden_size, num_layers, dropout)
        self.decoder = Decoder(vocab_size, embedding_dim, hidden_size, num_layers, dropout)
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
    def forward(self, src, trg, teacher_forcing_ratio=0.5):
        batch_size = src.size(0)
        trg_len = trg.size(1)
        vocab_size = self.decoder.vocab_size
        
        encoder_outputs, (hidden, cell) = self.encoder(src)
        decoder_hidden = hidden[:self.num_layers]
        decoder_cell = cell[:self.num_layers]
        
        outputs = torch.zeros(batch_size, trg_len, vocab_size).to(src.device)
        input_token = trg[:, 0:1]
        
        for t in range(1, trg_len):
            output, decoder_hidden, decoder_cell, attention = self.decoder(
                input_token, decoder_hidden, decoder_cell, encoder_outputs
            )
            
            outputs[:, t:t+1] = output
            
            use_teacher_forcing = random.random() < teacher_forcing_ratio
            if use_teacher_forcing:
                input_token = trg[:, t:t+1]
            else:
                input_token = output.argmax(dim=2)
        
        return outputs
    
    def translate(self, src, tokenizer, max_length=512):
        """Translate Python code to C code"""
        self.eval()
        with torch.no_grad():
            encoder_outputs, (hidden, cell) = self.encoder(src)
            decoder_hidden = hidden[:self.num_layers]
            decoder_cell = cell[:self.num_layers]
            
            input_token = torch.tensor([[tokenizer.token_to_id['<SOS>']]]).to(src.device)
            result = []
            
            for _ in range(max_length):
                output, decoder_hidden, decoder_cell, attention = self.decoder(
                    input_token, decoder_hidden, decoder_cell, encoder_outputs
                )
                
                predicted_token = output.argmax(dim=2)
                token_id = predicted_token.item()
                
                if token_id == tokenizer.token_to_id['<EOS>']:
                    break
                
                result.append(token_id)
                input_token = predicted_token
            
            return result

class CodeTranslator:
    """Main class for Python to C code translation"""
    
    def __init__(self, embedding_dim=256, hidden_size=512, num_layers=2, dropout=0.1):
        self.tokenizer = CodeTokenizer()
        self.model = None
        self.embedding_dim = embedding_dim
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.training_data = []
        
    def add_training_example(self, python_code, c_code):
        """Add a training example"""
        self.training_data.append((python_code, c_code))
    
    def clear_training_data(self):
        """Clear all training data"""
        self.training_data = []
    
    def save_training_data(self, filepath):
        """Save training data to JSON file"""
        data = [{"python": py, "c": c} for py, c in self.training_data]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load_training_data(self, filepath):
        """Load training data from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.training_data = []
            for item in data:
                if 'python' in item and 'c' in item:
                    self.training_data.append((item['python'], item['c']))
                    
            return True
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False
    
    def train(self, epochs=50, batch_size=4, learning_rate=0.001, progress_callback=None):
        """Train the model"""
        if not self.training_data:
            raise ValueError("No training data available. Add training examples first.")
        
        # Build vocabulary
        self.tokenizer.build_vocab(self.training_data)
        
        # Create model
        self.model = Seq2SeqTranslator(
            vocab_size=self.tokenizer.vocab_size,
            embedding_dim=self.embedding_dim,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout
        )
        
        # Create dataset and dataloader
        dataset = CodeDataset(self.training_data, self.tokenizer)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Setup training
        criterion = nn.CrossEntropyLoss(ignore_index=self.tokenizer.token_to_id['<PAD>'])
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            for batch_idx, (src, trg) in enumerate(dataloader):
                optimizer.zero_grad()
                
                output = self.model(src, trg)
                
                output = output[:, 1:].contiguous().view(-1, self.tokenizer.vocab_size)
                trg = trg[:, 1:].contiguous().view(-1)
                
                loss = criterion(output, trg)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(dataloader)
            
            if progress_callback:
                progress_callback(epoch + 1, epochs, avg_loss)
    
    def translate(self, python_code):
        """Translate Python code to C code"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        tokens = [self.tokenizer.token_to_id['<SOS>']] + self.tokenizer.encode(python_code) + [self.tokenizer.token_to_id['<EOS>']]
        tokens = tokens[:512]
        tokens = tokens + [self.tokenizer.token_to_id['<PAD>']] * (512 - len(tokens))
        
        src_tensor = torch.tensor([tokens], dtype=torch.long)
        result_tokens = self.model.translate(src_tensor, self.tokenizer)
        
        return self.tokenizer.decode(result_tokens)
    
    def save_model(self, filepath):
        """Save the trained model"""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
            
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'tokenizer': self.tokenizer,
            'model_params': {
                'embedding_dim': self.embedding_dim,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'dropout': self.dropout
            }
        }, filepath)
    
    def load_model(self, filepath):
        """Load a trained model"""
        checkpoint = torch.load(filepath, map_location='cpu')
        self.tokenizer = checkpoint['tokenizer']
        params = checkpoint['model_params']
        
        self.model = Seq2SeqTranslator(
            vocab_size=self.tokenizer.vocab_size,
            embedding_dim=params['embedding_dim'],
            hidden_size=params['hidden_size'],
            num_layers=params['num_layers'],
            dropout=params['dropout']
        )
        
        self.model.load_state_dict(checkpoint['model_state_dict'])

class TrainingGUI:
    """GUI for training the model with user data"""
    
    def __init__(self, translator):
        self.translator = translator
        self.root = tk.Tk()
        self.root.title("Python to C Code Translator - Training Interface")
        self.root.geometry("1200x800")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Python to C Code Translator Training", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Add Training Example", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)
        
        # Python code input
        ttk.Label(input_frame, text="Python Code:").grid(row=0, column=0, sticky=tk.W)
        self.python_text = scrolledtext.ScrolledText(input_frame, height=8, width=50)
        self.python_text.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # C code input
        ttk.Label(input_frame, text="C Code:").grid(row=0, column=1, sticky=tk.W)
        self.c_text = scrolledtext.ScrolledText(input_frame, height=8, width=50)
        self.c_text.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Add Example", command=self.add_example).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear Fields", command=self.clear_fields).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Data", command=self.load_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Data", command=self.save_data).pack(side=tk.LEFT, padx=5)
        
        # Training data list
        list_frame = ttk.LabelFrame(main_frame, text="Training Examples", padding="10")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for training data
        self.tree = ttk.Treeview(list_frame, columns=('Python', 'C'), show='headings', height=10)
        self.tree.heading('Python', text='Python Code')
        self.tree.heading('C', text='C Code')
        self.tree.column('Python', width=400)
        self.tree.column('C', width=400)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Training controls
        train_frame = ttk.LabelFrame(main_frame, text="Training Controls", padding="10")
        train_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Training parameters
        param_frame = ttk.Frame(train_frame)
        param_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(param_frame, text="Epochs:").grid(row=0, column=0, sticky=tk.W)
        self.epochs_var = tk.StringVar(value="50")
        ttk.Entry(param_frame, textvariable=self.epochs_var, width=10).grid(row=0, column=1, padx=(5, 15))
        
        ttk.Label(param_frame, text="Batch Size:").grid(row=0, column=2, sticky=tk.W)
        self.batch_var = tk.StringVar(value="4")
        ttk.Entry(param_frame, textvariable=self.batch_var, width=10).grid(row=0, column=3, padx=(5, 15))
        
        ttk.Label(param_frame, text="Learning Rate:").grid(row=0, column=4, sticky=tk.W)
        self.lr_var = tk.StringVar(value="0.001")
        ttk.Entry(param_frame, textvariable=self.lr_var, width=10).grid(row=0, column=5, padx=(5, 0))
        
        # Training button and progress
        train_button_frame = ttk.Frame(train_frame)
        train_button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.train_button = ttk.Button(train_button_frame, text="Start Training", command=self.start_training)
        self.train_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(train_button_frame, text="Save Model", command=self.save_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(train_button_frame, text="Load Model", command=self.load_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(train_button_frame, text="Open Editor", command=self.open_editor).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(train_frame, length=400, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        # Status label
        self.status_label = ttk.Label(train_frame, text="Ready to train")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=(5, 0))
        
        # Update display
        self.update_display()
        
    def add_example(self):
        """Add training example"""
        python_code = self.python_text.get("1.0", tk.END).strip()
        c_code = self.c_text.get("1.0", tk.END).strip()
        
        if not python_code or not c_code:
            messagebox.showwarning("Warning", "Please enter both Python and C code.")
            return
        
        self.translator.add_training_example(python_code, c_code)
        self.update_display()
        self.clear_fields()
        messagebox.showinfo("Success", "Training example added!")
        
    def clear_fields(self):
        """Clear input fields"""
        self.python_text.delete("1.0", tk.END)
        self.c_text.delete("1.0", tk.END)
        
    def update_display(self):
        """Update the training data display"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add training examples
        for py_code, c_code in self.translator.training_data:
            # Truncate long code for display
            py_display = py_code[:100] + "..." if len(py_code) > 100 else py_code
            c_display = c_code[:100] + "..." if len(c_code) > 100 else c_code
            self.tree.insert("", tk.END, values=(py_display, c_display))
        
        # Update status
        count = len(self.translator.training_data)
        self.status_label.config(text=f"Training examples: {count}")
        
    def load_data(self):
        """Load training data from file"""
        filepath = filedialog.askopenfilename(
            title="Load Training Data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            if self.translator.load_training_data(filepath):
                self.update_display()
                messagebox.showinfo("Success", f"Loaded {len(self.translator.training_data)} training examples.")
            else:
                messagebox.showerror("Error", "Failed to load training data.")
                
    def save_data(self):
        """Save training data to file"""
        if not self.translator.training_data:
            messagebox.showwarning("Warning", "No training data to save.")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save Training Data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            self.translator.save_training_data(filepath)
            messagebox.showinfo("Success", "Training data saved successfully.")
            
    def start_training(self):
        """Start training in a separate thread"""
        if not self.translator.training_data:
            messagebox.showwarning("Warning", "No training data available.")
            return
        
        try:
            epochs = int(self.epochs_var.get())
            batch_size = int(self.batch_var.get())
            learning_rate = float(self.lr_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid training parameters.")
            return
        
        self.train_button.config(state='disabled')
        self.progress['value'] = 0
        self.status_label.config(text="Training in progress...")
        
        def training_thread():
            try:
                self.translator.train(
                    epochs=epochs,
                    batch_size=batch_size,
                    learning_rate=learning_rate,
                    progress_callback=self.update_progress
                )
                self.root.after(0, self.training_complete)
            except Exception as e:
                self.root.after(0, lambda: self.training_error(str(e)))
        
        thread = threading.Thread(target=training_thread)
        thread.daemon = True
        thread.start()
        
    def update_progress(self, current_epoch, total_epochs, loss):
        """Update training progress"""
        progress = (current_epoch / total_epochs) * 100
        self.root.after(0, lambda: self.progress.config(value=progress))
        self.root.after(0, lambda: self.status_label.config(text=f"Epoch {current_epoch}/{total_epochs}, Loss: {loss:.4f}"))
        
    def training_complete(self):
        """Called when training is complete"""
        self.train_button.config(state='normal')
        self.progress['value'] = 100
        self.status_label.config(text="Training completed successfully!")
        messagebox.showinfo("Success", "Model training completed!")
        
    def training_error(self, error_msg):
        """Called when training fails"""
        self.train_button.config(state='normal')
        self.progress['value'] = 0
        self.status_label.config(text="Training failed.")
        messagebox.showerror("Error", f"Training failed: {error_msg}")
        
    def save_model(self):
        """Save the trained model"""
        if self.translator.model is None:
            messagebox.showwarning("Warning", "No trained model to save.")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save Model",
            defaultextension=".pth",
            filetypes=[("PyTorch files", "*.pth"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.translator.save_model(filepath)
                messagebox.showinfo("Success", "Model saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save model: {str(e)}")
                
    def load_model(self):
        """Load a trained model"""
        filepath = filedialog.askopenfilename(
            title="Load Model",
            filetypes=[("PyTorch files", "*.pth"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.translator.load_model(filepath)
                messagebox.showinfo("Success", "Model loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load model: {str(e)}")
                
    def open_editor(self):
        """Open the translation editor"""
        if self.translator.model is None:
            messagebox.showwarning("Warning", "Please train or load a model first.")
            return
        
        EditorGUI(self.translator)
        
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

class EditorGUI:
    """GUI for testing translations"""
    
    def __init__(self, translator):
        self.translator = translator
        self.root = tk.Toplevel()
        self.root.title("Python to C Code Translator - Editor")
        self.root.geometry("1000x600")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Python to C Code Translator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Python input
        python_frame = ttk.LabelFrame(main_frame, text="Python Code", padding="10")
        python_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        python_frame.columnconfigure(0, weight=1)
        python_frame.rowconfigure(0, weight=1)
        
        self.python_input = scrolledtext.ScrolledText(python_frame, height=20, width=40)
        self.python_input.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # C output
        c_frame = ttk.LabelFrame(main_frame, text="C Code Output", padding="10")
        c_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        c_frame.columnconfigure(0, weight=1)
        c_frame.rowconfigure(0, weight=1)
        
        self.c_output = scrolledtext.ScrolledText(c_frame, height=20, width=40, state='disabled')
        self.c_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Translation button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))
        
        self.translate_button = ttk.Button(
            button_frame, 
            text="Translate Python to C", 
            command=self.translate,
            width=20
        )
        self.translate_button.pack()
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Ready to translate")
        self.status_label.pack(pady=(10, 0))
        
        # Configure grid weights
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
    def translate(self):
        """Translate Python code to C code"""
        python_code = self.python_input.get("1.0", tk.END).strip()
        
        if not python_code:
            self.status_label.config(text="Please enter Python code to translate")
            return
        
        self.status_label.config(text="Translating...")
        self.translate_button.config(state='disabled')
        
        try:
            # Perform translation
            c_code = self.translator.translate(python_code)
            
            # Display results
            self.c_output.config(state='normal')
            self.c_output.delete("1.0", tk.END)
            self.c_output.insert(tk.END, c_code)
            self.c_output.config(state='disabled')
            
            self.status_label.config(text="Translation complete!")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            messagebox.showerror("Translation Error", f"Failed to translate code: {str(e)}")
        finally:
            self.translate_button.config(state='normal')

# Main entry point
if __name__ == "__main__":
    translator = CodeTranslator()
    gui = TrainingGUI(translator)
    gui.run()
