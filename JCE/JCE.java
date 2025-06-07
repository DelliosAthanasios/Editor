import javax.swing.*;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.table.*;
import java.awt.*;
import java.awt.event.*;
import java.io.PrintWriter;

public class JCE extends JFrame {
    private static final int MaxRows = 100;
    private static final int MaxCols = 100;

    private int Rows, Cols;
    private JTable table;
    private JLabel statusLabel;

    public JCE(int rows, int cols) {
        this.Rows = Math.min(rows, MaxRows);
        this.Cols = Math.min(cols, MaxCols);

        setTitle("JCE - Java Cell Editor");
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        // Top panel with buttons and status label
        JPanel topPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton saveBtn = new JButton("Save (F1)");
        JButton exitBtn = new JButton("Exit (F2)");
        statusLabel = new JLabel("Active cell: A1");

        topPanel.add(saveBtn);
        topPanel.add(exitBtn);
        topPanel.add(statusLabel);

        add(topPanel, BorderLayout.NORTH);

        // Setup table model and JTable
        DefaultTableModel model = new DefaultTableModel(Rows, Cols) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return true; // all cells editable
            }
        };

        table = new JTable(model);
        table.setCellSelectionEnabled(true);

        // Set column headers as A, B, C...
        JTableHeader header = table.getTableHeader();
        TableColumnModel colModel = table.getColumnModel();
        for (int c = 0; c < Cols; c++) {
            TableColumn col = colModel.getColumn(c);
            col.setHeaderValue(getColumnNameFromIndex(c));
        }
        header.repaint();

        JScrollPane scrollPane = new JScrollPane(table);
        add(scrollPane, BorderLayout.CENTER);

        // Listen for selection changes to update active cell label
        ListSelectionListener selectionListener = new ListSelectionListener() {
            public void valueChanged(ListSelectionEvent e) {
                updateActiveCellLabel();
            }
        };
        table.getSelectionModel().addListSelectionListener(selectionListener);
        table.getColumnModel().getSelectionModel().addListSelectionListener(selectionListener);

        // Save button action
        saveBtn.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent e) {
                saveFile();
            }
        });

        // Exit button action
        exitBtn.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent e) {
                System.exit(0);
            }
        });

        // Key bindings for WASD + arrow keys + F1/F2
        setupKeyBindings();

        setSize(Math.min(Cols * 75, 1000), Math.min(Rows * 20 + 100, 700));
        setLocationRelativeTo(null);
        setVisible(true);

        // Start selection at [0,0]
        table.changeSelection(0, 0, false, false);
    }

    private void updateActiveCellLabel() {
        int row = table.getSelectedRow();
        int col = table.getSelectedColumn();
        if (row >= 0 && col >= 0) {
            String cellRef = getColumnNameFromIndex(col) + (row + 1);
            statusLabel.setText("Active cell: " + cellRef);
        }
    }

    private void setupKeyBindings() {
        InputMap im = table.getInputMap(JComponent.WHEN_ANCESTOR_OF_FOCUSED_COMPONENT);
        ActionMap am = table.getActionMap();

        // WASD keys
        im.put(KeyStroke.getKeyStroke('W'), "moveUp");
        im.put(KeyStroke.getKeyStroke('w'), "moveUp");
        im.put(KeyStroke.getKeyStroke('S'), "moveDown");
        im.put(KeyStroke.getKeyStroke('s'), "moveDown");
        im.put(KeyStroke.getKeyStroke('A'), "moveLeft");
        im.put(KeyStroke.getKeyStroke('a'), "moveLeft");
        im.put(KeyStroke.getKeyStroke('D'), "moveRight");
        im.put(KeyStroke.getKeyStroke('d'), "moveRight");

        am.put("moveUp", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                moveSelection(-1, 0);
            }
        });
        am.put("moveDown", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                moveSelection(1, 0);
            }
        });
        am.put("moveLeft", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                moveSelection(0, -1);
            }
        });
        am.put("moveRight", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                moveSelection(0, 1);
            }
        });

        // F1 Save
        im.put(KeyStroke.getKeyStroke(KeyEvent.VK_F1, 0), "saveFile");
        am.put("saveFile", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                saveFile();
            }
        });

        // F2 Exit
        im.put(KeyStroke.getKeyStroke(KeyEvent.VK_F2, 0), "exitApp");
        am.put("exitApp", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                System.exit(0);
            }
        });
    }

    private void moveSelection(int rowDelta, int colDelta) {
        int row = table.getSelectedRow();
        int col = table.getSelectedColumn();
        int newRow = Math.min(Math.max(row + rowDelta, 0), Rows - 1);
        int newCol = Math.min(Math.max(col + colDelta, 0), Cols - 1);
        table.changeSelection(newRow, newCol, false, false);
    }

    private String getColumnNameFromIndex(int index) {
        // Convert 0 -> A, 25 -> Z, 26 -> AA, 27 -> AB ...
        StringBuilder sb = new StringBuilder();
        int num = index;
        do {
            sb.insert(0, (char) ('A' + (num % 26)));
            num = (num / 26) - 1;
        } while (num >= 0);
        return sb.toString();
    }

    private void saveFile() {
        String filename = JOptionPane.showInputDialog(this, "Enter filename to save:");
        if (filename == null || filename.trim().isEmpty())
            return;

        try (PrintWriter out = new PrintWriter(filename + ".csv")) {
            TableModel model = table.getModel();
            for (int r = 0; r < Rows; r++) {
                StringBuilder line = new StringBuilder();
                for (int c = 0; c < Cols; c++) {
                    Object val = model.getValueAt(r, c);
                    String cellText = val == null ? "" : val.toString();
                    // Escape commas & quotes for CSV
                    if (cellText.contains(",") || cellText.contains("\"")) {
                        cellText = "\"" + cellText.replace("\"", "\"\"") + "\"";
                    }
                    line.append(cellText);
                    if (c < Cols - 1)
                        line.append(",");
                }
                out.println(line.toString());
            }
            JOptionPane.showMessageDialog(this, "Saved to " + filename + ".csv");
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Error saving file: " + e.getMessage());
        }
    }

    private static int askDimension(String message, int max) {
        while (true) {
            String input = JOptionPane.showInputDialog(null, message + " (max " + max + "):");
            if (input == null)
                System.exit(0);
            try {
                int val = Integer.parseInt(input);
                if (val >= 1 && val <= max)
                    return val;
            } catch (NumberFormatException ignored) {
            }
            JOptionPane.showMessageDialog(null, "Please enter a valid number between 1 and " + max);
        }
    }

    public static void main(String[] args) {
        final int rows = askDimension("Enter number of rows", MaxRows);
        final int cols = askDimension("Enter number of columns", MaxCols);

        SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                new JCE(rows, cols);
            }
        });
    }
}
