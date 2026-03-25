# ccfddl cli

WIP

## install

```bash
pip install -r req.txt
python setup.py install
```

## usage

```bash
python -m ccfddl
```

| Argument | Type  | Description                          | Example            |
| -------- | ----- | ------------------------------------ | ------------------ |
| `--conf` | str[] | A list of conference IDs to filter.  | `--conf CVPR ICCV` |
| `--sub`  | str[] | A list of subcategory IDs to filter. | `--sub AI ML`      |
| `--rank` | str[] | A list of ranks to filter.           | `--rank A B`       |
